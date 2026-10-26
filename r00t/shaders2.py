"""GLSL v2: retro world + hack layer. Re-uses VERT / KAL / FB / BRIGHT / BLUR / TEXT_* from shaders.py."""
from .shaders import VERT, COMMON, KAL, FB, BRIGHT, BLUR, TEXT_V, TEXT_F  # noqa: F401

SCENE2 = "#version 330\n" + COMMON + """
uniform vec2 u_res;
uniform float u_t, u_dist, u_bass, u_lowmid, u_mid, u_high, u_rms, u_kick, u_snare, u_hat, u_wob;
uniform float u_hack, u_sun, u_city, u_neon, u_pal, u_shatter, u_zoom, u_rainN, u_moon, u_night, u_dusk;
uniform vec3 u_car, u_car2;
uniform int u_sA, u_sB;
uniform float u_mix;
uniform vec4 u_aA, u_aB;
uniform sampler2D u_spec, u_rain;
in vec2 uv;
out vec4 fragColor;

const vec3 PINK   = vec3(1.00,0.18,0.58);
const vec3 VIOLET = vec3(0.54,0.17,1.00);
const vec3 BLUE   = vec3(0.18,0.42,1.00);
const vec3 CYAN   = vec3(0.00,0.90,1.00);
const vec3 ORANGE = vec3(1.00,0.55,0.15);
const vec3 YELLOW = vec3(1.00,0.88,0.30);

vec3 grad4(float t, vec3 c0, vec3 c1, vec3 c2, vec3 c3){
  t = fract(t)*4.0; float f = fract(t); f = f*f*(3.0-2.0*f); int i = int(floor(t));
  if(i==0) return mix(c0,c1,f);
  if(i==1) return mix(c1,c2,f);
  if(i==2) return mix(c2,c3,f);
  return mix(c3,c0,f);
}
vec3 palI(float t, int k){
  if(k==0) return grad4(t, PINK, VIOLET, BLUE, CYAN);
  if(k==1) return grad4(t, vec3(1.0), CYAN, PINK, vec3(0.85,0.92,1.0));
  return grad4(t, vec3(1.0,0.10,0.20), vec3(1.0), PINK, vec3(1.0,0.40,0.10));
}
vec3 pal(float t, float id){
  float i0 = floor(id); float f = fract(id);
  return mix(palI(t,int(i0)), palI(t,min(int(i0)+1,2)), f);
}
float gline(float v, float w){
  float fw = fwidth(v)*0.9;
  float d = abs(fract(v+0.5)-0.5);
  return smoothstep(w+fw, max(w-fw,0.0), d);
}
float vnoise(vec2 p){ vec2 i=floor(p), f=fract(p); f=f*f*(3.0-2.0*f);
  return mix(mix(hash21(i),hash21(i+vec2(1,0)),f.x), mix(hash21(i+vec2(0,1)),hash21(i+vec2(1,1)),f.x), f.y); }
float fbm(vec2 p){ float a=0.5,s=0.0; for(int i=0;i<4;i++){ s+=a*vnoise(p); p=p*2.03+vec2(11.3,7.7); a*=0.5; } return s; }
float specAt(float x){ return texture(u_spec, vec2(clamp(x,0.0,0.999),0.5)).r; }


// ------------------------------------------------------------------ rear-view neon car (real object: perspective, tail lights, underglow)
float cBox(vec2 p, vec2 b, float r){ vec2 d=abs(p)-b+r; return length(max(d,0.0))+min(max(d.x,d.y),0.0)-r; }
vec4 carRear(vec2 q, float brake){
  float body = cBox(q-vec2(0.0,0.36), vec2(0.88,0.20), 0.09);
  float tap = mix(0.64,0.46, clamp((q.y-0.54)/0.36,0.0,1.0));
  float cab = max(max(abs(q.x)-tap, q.y-0.90), 0.52-q.y);
  float sp = cBox(q-vec2(0.0,0.66), vec2(0.80,0.028), 0.01);
  float w1 = cBox(q-vec2(-0.64,0.15), vec2(0.15,0.15), 0.05);
  float w2 = cBox(q-vec2( 0.64,0.15), vec2(0.15,0.15), 0.05);
  float d = min(min(body,cab),min(sp,min(w1,w2)));
  float a = smoothstep(0.014,-0.004,d);
  if(a<=0.001) return vec4(0.0);
  vec3 c = mix(vec3(0.05,0.0,0.10), vec3(0.015,0.0,0.05), clamp(q.y,0.0,1.0));
  float rim = smoothstep(0.045,0.0,-d)*smoothstep(0.30,0.55,q.y);
  c += vec3(0.0,0.75,1.0)*rim*1.1;
  float win = cBox(q-vec2(0.0,0.72), vec2(tap*0.78,0.11), 0.05);
  c = mix(c, vec3(0.20,0.05,0.34)*(0.6+0.8*(1.0-q.y)), smoothstep(0.01,-0.01,win)*0.9);
  float tl = min(cBox(q-vec2(0.0,0.42), vec2(0.70,0.022), 0.01), min(cBox(q-vec2(-0.74,0.40), vec2(0.11,0.075), 0.03), cBox(q-vec2(0.74,0.40), vec2(0.11,0.075), 0.03)));
  c = mix(c, vec3(1.0,0.06,0.16)*(1.7+3.2*brake), smoothstep(0.012,-0.004,tl));
  float wh = min(w1,w2);
  c = mix(c, vec3(0.01,0.0,0.03), smoothstep(0.01,-0.004,wh)*0.9);
  return vec4(c, a);
}

// ------------------------------------------------------------------ 0: RETRO WORLD (synthwave that can be hacked)
vec3 sceneWorld(vec2 p, vec4 a){
  float h = u_hack;
  float dir = a.y;
  float hz = -0.18;
  // block tearing
  float rowb = floor(p.y*34.0);
  float gk = hash21(vec2(rowb, floor(u_t*11.0)));
  p.x += (gk-0.5)*0.16*h*step(1.0-0.55*h, gk);
  // sky
  float sy = clamp((p.y-hz)/(1.0-hz),0.0,1.0);
  vec3 col = mix(vec3(1.0,0.50,0.20), vec3(0.98,0.20,0.52), smoothstep(0.0,0.10,sy));
  col = mix(col, vec3(0.34,0.05,0.52), smoothstep(0.08,0.46,sy));
  col = mix(col, vec3(0.035,0.0,0.15), smoothstep(0.40,0.96,sy));
  col *= 0.55+0.45*u_neon;
  col = mix(col, mix(vec3(1.0,0.30,0.10), vec3(0.22,0.03,0.32), smoothstep(0.0,0.5,sy)), u_dusk*0.8*(1.0-u_night));
  col = mix(col, mix(vec3(0.16,0.05,0.38), vec3(0.008,0.0,0.05), smoothstep(0.0,0.55,sy)), u_night);
  // stars
  if(p.y>hz){
    vec2 g = p*vec2(58.0,58.0); vec2 id = floor(g); float hh = hash21(id);
    vec2 f = fract(g)-0.5+(hash22(id)-0.5)*0.5;
    float s = smoothstep(0.14,0.0,length(f))*step(0.92-0.05*u_night,hh);
    s *= 0.45+0.55*sin(u_t*3.0+hh*60.0);
    col += s*vec3(1.0)*(1.0+u_hat*3.0+2.5*u_night)*smoothstep(hz+0.1,0.5,p.y);
  }
  // sun
  float sr = 0.34*(1.0+0.07*u_bass+0.07*u_kick);
  vec2 sc = vec2(0.0, mix(hz-sr-0.06, hz+0.42, u_sun));
  float d = length(p-sc);
  float ky = clamp((p.y-(sc.y-sr))/(2.0*sr),0.0,1.0);
  vec3 sunCol = mix(vec3(1.0,0.16,0.52), vec3(1.0,0.50,0.16), smoothstep(0.05,0.55,ky));
  sunCol = mix(sunCol, vec3(1.0,0.90,0.32), smoothstep(0.50,1.0,ky));
  sunCol = mix(sunCol, mix(vec3(1.0,0.22,0.06), vec3(1.0,0.5,0.1), ky), u_dusk*0.85);
  float disk = smoothstep(sr, sr-0.012, d)*step(hz,p.y);
  float slit = smoothstep(0.58,0.0,ky);
  float bandv = fract(p.y*13.0+u_t*0.10);
  disk *= 1.0-(1.0-smoothstep(slit*0.8-0.03,slit*0.8+0.03,bandv));
  // pixel dissolve (system hacked)
  vec2 cell = floor(p*vec2(30.0,30.0));
  float hb = hash21(cell+floor(u_t*9.0));
  float dis = step(hb, h*1.15*(1.15-ky*0.7));
  disk *= 1.0-dis*(0.35+0.65*mod(cell.x+cell.y,2.0));
  vec3 halo = mix(PINK, ORANGE, 0.5)*exp(-max(d-sr,0.0)*4.0)*(0.5+0.8*u_bass)*step(hz,p.y);
  col += halo*u_sun*0.9;
  col = mix(col, sunCol*(1.25+0.5*u_kick), disk);
  vec2 mc = vec2(-0.34, mix(hz-0.32, hz+0.66, u_moon));
  float mr = 0.16;
  float dm = length(p-mc);
  float mv = smoothstep(0.0,0.08,u_moon);
  vec2 mq = (p-mc)/mr;
  float mz = sqrt(max(1.0-dot(mq,mq),0.0));
  float lit = 0.62+0.38*dot(normalize(vec3(mq,mz+0.001)), normalize(vec3(-0.5,0.55,0.65)));
  float cr = fbm(mq*3.2+vec2(4.0,1.0));
  vec3 moonCol = mix(vec3(0.55,0.64,0.95), vec3(0.97,0.98,1.0), lit)*(0.80+0.34*cr);
  col += vec3(0.30,0.42,1.0)*exp(-max(dm-mr,0.0)*4.5)*0.6*mv*step(hz,p.y)*(0.6+0.5*u_bass);
  col = mix(col, moonCol*1.2, smoothstep(mr,mr-0.006,dm)*step(hz,p.y)*mv);
  // far mountains
  float mh = hz+0.03+0.13*pow(fbm(vec2(p.x*2.4+3.0,1.7)),1.7);
  if(p.y>hz && p.y<mh){
    vec3 m = mix(vec3(0.07,0.0,0.18), PINK*0.28, smoothstep(mh-0.07,mh,p.y));
    col = m;
  }
  col += PINK*0.9*smoothstep(0.004,0.0,abs(p.y-mh))*step(hz,p.y)*u_neon*0.5;
  // skyline
  float bw = 24.0;
  float bid = floor(p.x*bw);
  float jit = (hash11(bid+floor(u_t*7.0))-0.5)*0.03*h*step(0.55,hash11(bid*3.1+floor(u_t*7.0)));
  float bh = (0.03+0.23*pow(hash11(bid*1.37+3.0),1.6))*(0.55+0.45*smoothstep(0.75,0.0,abs(p.x)))*u_city;
  bh += jit*0.0;
  if(p.y>hz && p.y<hz+bh){
    vec3 b = vec3(0.025,0.0,0.09);
    vec2 wc = vec2(fract(p.x*bw)*4.0,(p.y-hz)*70.0);
    vec2 wid = vec2(floor(wc.x)+bid*7.0, floor(wc.y));
    float lit = step(0.60,hash21(wid))*step(0.15,fract(wc.x))*step(fract(wc.x),0.85)*step(0.2,fract(wc.y))*step(fract(wc.y),0.8);
    lit *= step(0.35, fract(hash21(wid+9.0)*5.0+u_t*(0.15+0.3*hash21(wid)+2.0*h)));
    vec3 wcol = (hash21(wid+3.0)>0.5) ? CYAN : (hash21(wid+5.0)>0.5 ? PINK : YELLOW);
    b += lit*wcol*(1.0+u_hat*2.5)*1.2;
    col = b;
  }
  col += CYAN*smoothstep(0.005,0.0,abs(p.y-(hz+bh)))*step(0.001,bh)*step(hz,p.y)*u_neon*0.8;
  // floor
  if(p.y<hz){
    float dy = hz-p.y;
    float z = 0.30/dy;
    float x = p.x*z*1.3;
    float wz = z*0.9+dir*u_dist;
    // grid dropouts under attack
    float drop = step(hash21(vec2(floor(wz*0.8), floor(x*0.9))+floor(u_t*6.0)), 0.55*h);
    float lz = gline(wz,0.012)*(1.0-drop);
    float lx = gline(x*0.9+0.5,0.012)*(1.0-drop);
    float fade = smoothstep(0.0,0.26,dy);
    vec3 base = mix(vec3(0.08,0.0,0.20), vec3(0.05,0.02,0.28), smoothstep(0.0,0.9,dy));
    vec3 gcol = mix(CYAN, PINK, smoothstep(0.35,1.0,dy)*0.55+0.5*h);
    vec3 f = base + (lz+lx)*gcol*1.35*fade*u_neon*(0.7+1.2*u_bass+0.6*u_kick);
    f += mix(PINK,ORANGE,0.4)*exp(-abs(p.x)*2.3)*exp(-dy*3.4)*u_sun*(0.7+u_bass);
    f += vec3(0.35,0.5,1.0)*exp(-abs(p.x-mc.x)*3.2)*exp(-dy*3.0)*mv*(0.5+0.4*u_bass);
    col = f;
  }
  col += mix(PINK,ORANGE,0.5)*exp(-abs(p.y-hz)*40.0)*(1.0+u_bass*1.2)*u_neon*0.9;
  for(int ci=0; ci<2; ci++){
    vec3 cu = (ci==0)? u_car : u_car2;
    if(cu.x>0.001){
      float zc = cu.y;
      float s_ = 0.30/zc;
      float bx = cu.z/(zc*1.3);
      float by = hz - s_ + 0.010*u_bass*s_;
      vec2 q = vec2((p.x-bx)/s_, (p.y-by)/s_);
      vec4 cc = carRear(q, u_kick);
      float ug = exp(-length(vec2(q.x*0.55, (q.y+0.02)*5.0)))*step(q.y,0.12);
      col += mix(PINK,CYAN,0.35)*ug*0.9*cu.x;
      col += vec3(1.0,0.05,0.15)*exp(min(q.y,0.0)*2.2)*exp(-q.x*q.x*0.9)*step(q.y,0.0)*(0.25+0.5*u_kick)*cu.x*smoothstep(-1.3,-0.1,q.y);
      col = mix(col, cc.rgb, cc.a*cu.x);
    }
  }
  // hack tint: pull everything toward cyan/white terminal look
  float lum = dot(col,vec3(0.3,0.5,0.2));
  col = mix(col, vec3(lum)*vec3(0.75,1.0,1.1)+col*0.35, h*0.45);
  return col;
}

// ------------------------------------------------------------------ 1: NEON GRID TUNNEL
vec3 sceneTunnel(vec2 p, vec4 a){
  p = rot(a.z)*p;
  float r = max(abs(p.x),abs(p.y))+1e-3;
  float z = 0.42/r;
  float wz = z+u_dist;
  float u = (abs(p.x)>abs(p.y)) ? p.y/abs(p.x) : p.x/abs(p.y);
  float ring = gline(wz*0.55,0.025);
  float lineU = gline(u*3.0,0.03);
  float alt = step(0.5,fract(floor(wz*0.55)*0.5));
  vec3 cr = mix(CYAN, PINK, alt);
  vec3 col = cr*ring*2.2 + mix(PINK,CYAN,alt)*lineU*1.3*smoothstep(0.0,0.5,r);
  col *= 0.30+0.70*smoothstep(0.0,0.45,r);
  col += pal(0.1,u_pal)*exp(-r*5.0)*(1.5+2.2*u_kick);
  // corner light streaks
  col += vec3(1.0)*gline(atan(p.y,p.x)*4.0/PI+0.5,0.01)*0.0;
  return col*(0.7+0.9*u_kick);
}

// ------------------------------------------------------------------ 2: MATRIX / KATAKANA RAIN
vec3 sceneMatrix(vec2 p, vec4 a){
  float cwid = 0.052, chgt = 0.088;
  vec2 g = vec2(p.x/cwid, p.y/chgt);
  float colI = floor(g.x);
  float act = step(0.25, hash11(colI*1.9));
  float spd = 0.5+1.5*hash11(colI*3.1);
  float off = hash11(colI*7.3)*60.0;
  float fall = (u_t*3.5+u_dist*0.25)*spd+off;
  float r = -g.y;
  float per = 28.0;
  float rh = mod(fall, per);
  float rr = mod(r, per);
  float dd = mod(rh-rr, per);
  float inten = exp(-dd*0.26)*act;
  float head = step(dd,1.0)*act;
  float gi = floor(hash21(vec2(colI, floor(r))+floor(u_t*(2.0+5.0*hash11(colI))))*u_rainN);
  vec2 f = vec2(fract(g.x), fract(g.y));
  float gm = texture(u_rain, vec2((gi+f.x)/u_rainN, 1.0-f.y)).r;
  vec3 body = pal(colI*0.05+u_t*0.06, u_pal);
  vec3 col = body*gm*inten*(1.0+0.8*u_rms)*1.3;
  col += vec3(1.0)*gm*head*2.0;
  col += body*exp(-dd*0.12)*act*0.05*(0.5+u_bass);
  return col*((a.w>0.01)?a.w:1.0);
}

// ------------------------------------------------------------------ 3: EQ RINGS + triangles
float polyD(vec2 p, float n, float rotA){
  float an = atan(p.y,p.x)+rotA; float s = TAU/n;
  return length(p)*cos(mod(an+s*0.5,s)-s*0.5);
}
vec3 sceneEQ(vec2 p, vec4 a){
  float r = length(p), ang = atan(p.y,p.x);
  float idx = abs(ang)/PI;
  float nb = 56.0;
  float bi = floor(idx*nb), bf = fract(idx*nb);
  float s = specAt((bi+0.5)/nb);
  float rb = 0.30, rtop = rb+0.06+0.62*pow(s,1.1)*(0.7+0.8*u_kick);
  float gap = smoothstep(0.0,0.2,bf)*smoothstep(1.0,0.8,bf);
  float bar = smoothstep(rb-0.005,rb+0.005,r)*smoothstep(rtop+0.01,rtop-0.01,r)*gap;
  vec3 col = pal(bi/nb+u_t*0.05,u_pal)*bar*1.5;
  col += pal(bi/nb+0.5,u_pal)*smoothstep(0.02,0.0,abs(r-rtop))*gap*1.2*step(rb+0.07,rtop);
  col += CYAN*smoothstep(0.012,0.0,abs(r-(rb-0.02)))*1.6;
  for(int i=0;i<3;i++){
    float fi = float(i);
    float rad = 0.55+0.28*fi+0.05*sin(u_t*2.0+fi)+0.08*u_kick;
    float dd = polyD(p,3.0,(mod(fi,2.0)<0.5?1.0:-1.0)*u_t*0.5+fi*1.1);
    col += mix(PINK,CYAN,mod(fi,2.0))*smoothstep(0.012,0.0,abs(dd-rad))*(1.3+u_hat);
  }
  float kr = fract(u_t*2.2);
  col += PINK*smoothstep(0.015,0.0,abs(r-(0.3+kr*1.3)))*(1.0-kr)*0.8;
  col += pal(0.2,u_pal)*exp(-r*7.0)*(0.6+2.0*u_kick);
  return col*((a.w>0.01)?a.w:1.0);
}

// ------------------------------------------------------------------ 4: VOID (dark room, sprites do the talking)
vec3 sceneVoid(vec2 p, vec4 a){
  float r = length(p);
  vec3 col = vec3(0.012,0.0,0.035);
  col += pal(0.3+u_t*0.03,u_pal)*0.10*exp(-r*1.4)*(0.6+u_bass+0.8*u_kick);
  float gx = gline(p.x*5.0,0.01), gy = gline(p.y*5.0,0.01);
  col += pal(0.6,u_pal)*(gx+gy)*0.05*exp(-r*0.8);
  return col;
}

vec3 evalScene(int id, vec2 p, vec4 a){
  if(id==0) return sceneWorld(p,a);
  if(id==1) return sceneTunnel(p,a);
  if(id==2) return sceneMatrix(p,a);
  if(id==3) return sceneEQ(p,a);
  return sceneVoid(p,a);
}

vec2 shatterUV(vec2 p, out float edge){
  edge = 0.0;
  if(u_shatter<0.001) return p;
  vec2 g = p*3.0; vec2 ip = floor(g), fp = fract(g);
  float md = 9.0, md2 = 9.0; vec2 mc = vec2(0.0), mid = vec2(0.0);
  for(int j=-1;j<=1;j++) for(int i=-1;i<=1;i++){
    vec2 b = vec2(float(i),float(j)); vec2 o = hash22(ip+b);
    vec2 r = b+o-fp; float d = dot(r,r);
    if(d<md){ md2=md; md=d; mc=ip+b+o; mid=ip+b; } else if(d<md2){ md2=d; }
  }
  edge = smoothstep(0.07,0.0,sqrt(md2)-sqrt(md));
  vec2 h = hash22(mid*1.7+3.1);
  vec2 center = mc/3.0;
  float s = u_shatter;
  vec2 q = p-center;
  q = rot((h.x-0.5)*1.8*s)*q*(1.0+(h.y-0.5)*0.6*s);
  return center+q+(h-0.5)*0.5*s;
}

void main(){
  vec2 p = (uv-0.5)*vec2(u_res.x/u_res.y,1.0)*2.0;
  p /= max(u_zoom,0.05);
  float edge;
  vec2 ps = shatterUV(p, edge);
  vec3 col = evalScene(u_sA, ps, u_aA);
  if(u_mix>0.001){
    vec3 cb = evalScene(u_sB, ps, u_aB);
    col = mix(col, cb, smoothstep(0.0,1.0,u_mix));
  }
  col += edge*u_shatter*vec3(1.0,0.92,1.0)*2.4;
  fragColor = vec4(col,1.0);
}
"""

POST2 = "#version 330\n" + COMMON + """
uniform vec2 u_res;
uniform sampler2D u_comp, u_b1, u_b2, u_b3, u_b4, u_text;
uniform float u_t, u_bloom, u_ca, u_glit, u_flash, u_inv, u_black, u_fade, u_scan, u_grain, u_vig, u_pump, u_crt, u_dot, u_expo, u_sat, u_capdim;
uniform float u_vhs, u_pix, u_roll, u_tilt;
uniform vec3 u_flashcol;
uniform vec2 u_shake;
in vec2 uv;
out vec4 fragColor;
vec3 aces(vec3 x){ return clamp((x*(2.51*x+0.03))/(x*(2.43*x+0.59)+0.14),0.0,1.0); }
void main(){
  float asp = u_res.x/u_res.y;
  vec2 c0 = uv-0.5;
  float crtMask = 1.0;
  if(u_crt>0.0){
    float ph1 = clamp(u_crt/0.55,0.0,1.0), ph2 = clamp((u_crt-0.55)/0.35,0.0,1.0);
    float sy = mix(1.0, 0.004, ph1*ph1*(3.0-2.0*ph1));
    float sx = mix(1.0, 0.0, ph2);
    c0.y /= sy; c0.x /= max(sx,0.0005);
    if(abs(c0.y)>0.5 || abs(c0.x)>0.5) crtMask = 0.0;
  }
  c0 = rot(u_tilt)*(c0*vec2(asp,1.0))/vec2(asp,1.0);
  c0 /= (1.0+u_pump);
  vec2 q = c0+0.5+u_shake;
  q.y += u_roll;
  // VHS: tracking band, head-switching noise at the bottom, line jitter
  if(u_vhs>0.0){
    float bot = 1.0-smoothstep(0.0,0.07,uv.y);
    q.x += bot*u_vhs*0.05*(hash11(floor(uv.y*180.0)+floor(u_t*30.0))-0.5);
    float ty = fract(u_t*0.11+0.3);
    float tb = smoothstep(0.03,0.0,abs(uv.y-ty));
    q.x += tb*u_vhs*0.04*(hash11(floor(uv.y*220.0)+floor(u_t*40.0))-0.5)*2.0;
    q.x += u_vhs*0.0015*sin(uv.y*900.0+u_t*60.0);
  }
  // pixel dissolve (blocky transition)
  if(u_pix>0.001){
    float blk = mix(1.0, 56.0, u_pix);
    q = (floor(q*u_res/blk)+0.5)*blk/u_res;
  }
  float bl = floor(q.y*38.0);
  float gr = hash21(vec2(bl, floor(u_t*24.0)));
  float gon = step(1.0-0.55*u_glit, gr);
  q.x += gon*(hash21(vec2(bl,floor(u_t*24.0)+7.0))-0.5)*0.16*u_glit;
  vec2 dir = (q-0.5); float rr = length(dir*vec2(asp,1.0));
  vec2 off = dir*(u_ca*(0.4+rr*1.6));
  float cr = texture(u_comp, q+off).r, cg = texture(u_comp, q).g, cb = texture(u_comp, q-off).b;
  vec3 c = vec3(cr,cg,cb);
  vec3 bl_ = texture(u_b1,q).rgb*0.30 + texture(u_b2,q).rgb*0.22 + texture(u_b3,q).rgb*0.17 + texture(u_b4,q).rgb*0.12;
  c += bl_*u_bloom;
  c *= 1.0 - u_capdim*0.55*exp(-pow((uv.y-0.307)/0.075,2.0));
  c += u_flashcol*u_flash;
  c = mix(c, vec3(1.15)-c, u_inv);
  vec4 tx = texture(u_text, q);
  vec2 px = 1.0/u_res;
  vec3 tg = vec3(0.0);
  for(int k=0;k<8;k++){
    float a = float(k)*0.7853982;
    tg += texture(u_text, q+vec2(cos(a),sin(a))*px*9.0).rgb;
    tg += texture(u_text, q+vec2(cos(a),sin(a))*px*22.0).rgb*0.6;
  }
  c = c*(1.0-tx.a) + tx.rgb + tg*0.07;
  c = max(c-vec3(0.02),0.0);
  c *= u_expo;
  float lum = dot(c,vec3(0.299,0.587,0.114));
  c = mix(vec3(lum), c, u_sat);
  c = aces(c);
  c = pow(c, vec3(0.92));
  c *= 1.0-u_scan*(0.5+0.5*sin(q.y*u_res.y*3.14159));
  float vg = 1.0-u_vig*pow(length((uv-0.5)*vec2(1.0,1.15))*1.35,2.2);
  c *= clamp(vg,0.0,1.0);
  c += (hash21(uv*u_res+fract(u_t)*91.0)-0.5)*(u_grain+0.03*u_vhs);
  c += vec3(1.0)*u_dot*smoothstep(0.02+0.2*u_dot,0.0,length((uv-0.5)*vec2(asp,1.0)));
  c *= u_fade*(1.0-u_black)*crtMask;
  if(u_crt>0.0) c += vec3(0.8,0.9,1.0)*crtMask*smoothstep(0.3,0.0,abs(c0.y))*u_crt*0.6;
  fragColor = vec4(clamp(c,0.0,1.0),1.0);
}
"""

SPRITE_V = TEXT_V

SPRITE_F = """
#version 330
uniform sampler2D u_atlas, u_glyph;
uniform vec4 u_rect;
uniform vec2 u_size, u_cell, u_asz;
uniform float u_alpha, u_split, u_ascii, u_dissolve, u_slice, u_time, u_jit, u_glyphN, u_dsz;
uniform vec3 u_tint;
in vec2 tuv;
out vec4 fragColor;
float h21(vec2 p){ vec3 p3 = fract(vec3(p.xyx)*.1031); p3 += dot(p3,p3.yzx+33.33); return fract((p3.x+p3.y)*p3.z); }
vec4 atl(vec2 t){
  vec2 px = u_rect.xy + clamp(t,0.0,1.0)*u_rect.zw;
  return texture(u_atlas, px/u_asz);
}
vec4 spr(vec2 t){
  if(t.x<0.0||t.x>1.0) return vec4(0.0);
  if(u_ascii<0.001) return atl(t);
  vec2 local = t*u_size;
  vec2 cell = floor(local/u_cell);
  vec2 cc = (cell+0.5)*u_cell/u_size;
  vec2 d = u_cell/u_size*0.32;
  vec4 s = (atl(cc)+atl(cc+vec2(d.x,0.0))+atl(cc-vec2(d.x,0.0))+atl(cc+vec2(0.0,d.y))+atl(cc-vec2(0.0,d.y)))*0.2;
  float lum = dot(s.rgb, vec3(0.299,0.587,0.114));
  float n = h21(cell+floor(u_time*12.0));
  float gi = clamp(floor(lum*(u_glyphN-1.0)+(n-0.5)*u_jit*u_glyphN*0.25+0.5),0.0,u_glyphN-1.0);
  vec2 f = fract(local/u_cell);
  float gm = texture(u_glyph, vec2((gi+f.x)/u_glyphN, f.y)).r;
  float on = smoothstep(0.03,0.10,s.a);
  float v = gm*(0.30+1.25*lum)*on;
  vec4 a = vec4(vec3(v), v);
  vec4 o = atl(t);
  // keep thin bright wireframe lines from the source on top of the glyphs
  float line = smoothstep(0.82,1.0,o.r)*0.55;
  a += vec4(vec3(line), line)*on;
  return mix(o, a, u_ascii);
}
vec4 sprite_all(vec2 t){
  if(u_slice>0.0){
    float sl = floor(t.y*20.0);
    float hh = h21(vec2(sl, floor(u_time*20.0)));
    t.x += (hh-0.5)*u_slice*step(0.55,hh);
  }
  return spr(t);
}
void main(){
  float sp = u_split;
  vec4 cr = sprite_all(tuv+vec2(sp,0.0));
  vec4 cg = sprite_all(tuv);
  vec4 cb = sprite_all(tuv-vec2(sp,0.0));
  vec4 c = vec4(cr.r, cg.g, cb.b, max(cr.a,max(cg.a,cb.a)));
  if(u_dissolve>0.0){
    float hh = h21(floor(tuv*u_size/max(u_dsz,2.0))+floor(u_time*14.0));
    if(hh<u_dissolve) c = vec4(0.0);
    else if(hh<u_dissolve+0.07) c += vec4(0.0,0.9,1.0,1.0)*c.a*0.9;
  }
  c.rgb *= u_tint;
  fragColor = c*u_alpha;
}
"""
