"""GLSL for the 'We Own the Night' visualizer."""

VERT = """
#version 330
in vec2 pos;
out vec2 uv;
void main(){ uv = pos*0.5+0.5; gl_Position = vec4(pos,0.0,1.0); }
"""

COMMON = """
const float PI = 3.14159265;
const float TAU = 6.2831853;
mat2 rot(float a){ float c=cos(a), s=sin(a); return mat2(c,-s,s,c); }
float hash11(float p){ p = fract(p*.1031); p *= p+33.33; p *= p+p; return fract(p); }
float hash21(vec2 p){ vec3 p3 = fract(vec3(p.xyx)*.1031); p3 += dot(p3,p3.yzx+33.33); return fract((p3.x+p3.y)*p3.z); }
vec2 hash22(vec2 p){ vec3 p3 = fract(vec3(p.xyx)*vec3(.1031,.1030,.0973)); p3 += dot(p3,p3.yzx+33.33); return fract((p3.xx+p3.yz)*p3.zy); }
vec3 hueShift(vec3 c, float h){
  const mat3 toYIQ = mat3(0.299,0.596,0.211, 0.587,-0.274,-0.523, 0.114,-0.322,0.312);
  const mat3 toRGB = mat3(1.0,1.0,1.0, 0.956,-0.272,-1.106, 0.621,-0.647,1.703);
  vec3 y = toYIQ*c; float s=sin(h), co=cos(h); y.yz = mat2(co,-s,s,co)*y.yz; return toRGB*y;
}
"""

SCENE = "#version 330\n" + COMMON + """
uniform vec2 u_res;
uniform float u_t, u_dist, u_bass, u_lowmid, u_mid, u_high, u_rms, u_kick, u_snare, u_hat, u_wob;
uniform float u_pal, u_shatter, u_city, u_neon;
uniform int u_sA, u_sB;
uniform float u_mix;
uniform vec4 u_aA, u_aB;
uniform sampler2D u_spec;
in vec2 uv;
out vec4 fragColor;

// ------------------------------------------------------------------ palettes
vec3 grad4(float t, vec3 c0, vec3 c1, vec3 c2, vec3 c3){
  t = fract(t)*4.0; float f = fract(t); f = f*f*(3.0-2.0*f); int i = int(floor(t));
  if(i==0) return mix(c0,c1,f);
  if(i==1) return mix(c1,c2,f);
  if(i==2) return mix(c2,c3,f);
  return mix(c3,c0,f);
}
vec3 palI(float t, int k){
  if(k==0) return grad4(t, vec3(1.00,0.12,0.84), vec3(0.48,0.17,1.00), vec3(0.00,0.90,1.00), vec3(1.00,0.70,0.28));
  if(k==1) return grad4(t, vec3(0.00,0.94,1.00), vec3(1.00,0.00,0.67), vec3(1.00,1.00,1.00), vec3(0.36,0.17,1.00));
  if(k==2) return grad4(t, vec3(0.71,1.00,0.00), vec3(0.00,1.00,0.64), vec3(0.48,0.00,1.00), vec3(1.00,0.00,0.83));
  if(k==3) return grad4(t, vec3(1.00,0.10,0.10), vec3(1.00,0.48,0.00), vec3(1.00,0.88,0.29), vec3(1.00,0.30,0.55));
  if(k==4) return grad4(t, vec3(0.00,0.70,1.00), vec3(0.42,0.36,1.00), vec3(0.79,0.96,1.00), vec3(0.00,0.23,1.00));
  return grad4(t, vec3(1.00,0.84,0.54), vec3(1.00,0.31,0.63), vec3(0.23,0.10,0.43), vec3(0.00,0.76,1.00));
}
vec3 pal(float t, float id){
  float i0 = floor(id); float f = fract(id);
  return mix(palI(t,int(i0)), palI(t,min(int(i0)+1,5)), f);
}
float gline(float v, float w){
  float fw = fwidth(v)*0.9;
  float d = abs(fract(v+0.5)-0.5);
  return smoothstep(w+fw, max(w-fw,0.0), d);
}
float specAt(float x){ return texture(u_spec, vec2(clamp(x,0.0,0.999),0.5)).r; }

// ------------------------------------------------------------------ 0: OUTRUN (synthwave)
float gearShape(vec2 p, vec2 c, float R, float teeth, float ra, float w){
  vec2 q = p - c; float r = length(q); float a = atan(q.y,q.x) + ra;
  float Rr = R*(1.0 + 0.11*smoothstep(-0.3,0.3,sin(teeth*a)));
  float ring = smoothstep(w, 0.0, abs(r-Rr));
  float inner = smoothstep(w, 0.0, abs(r-R*0.45));
  float spokes = smoothstep(w, 0.0, abs(sin(3.0*a))*r) * step(r, R*0.9) * step(R*0.2, r);
  return ring + inner*0.8 + spokes*0.7;
}
vec3 sceneOutrun(vec2 p, vec4 a){
  float sun = a.x, dir = a.y, fail = a.z, gearsAmt = a.w;
  float hz = -0.16;
  // glitching / failing grid
  float gk = hash11(floor(p.y*28.0)+floor(u_t*12.0));
  p.x += fail*0.06*(gk-0.5)*step(1.0-fail*0.55, gk+0.2*fail);
  vec3 col;
  // sky
  float sy = clamp((p.y-hz)/(1.0-hz), 0.0, 1.0);
  vec3 skyTop = vec3(0.012,0.0,0.06);
  vec3 skyMid = pal(0.62,u_pal)*0.30;
  vec3 skyHor = pal(0.05,u_pal)*0.85;
  col = mix(skyHor, skyMid, smoothstep(0.0,0.38,sy));
  col = mix(col, skyTop, smoothstep(0.22,0.95,sy));
  // stars
  if(p.y>hz){
    vec2 g = p*vec2(60.0,60.0); vec2 id = floor(g); float h = hash21(id);
    vec2 f = fract(g)-0.5 + (hash22(id)-0.5)*0.5;
    float s = smoothstep(0.14,0.0,length(f))*step(0.92,h);
    s *= 0.45+0.55*sin(u_t*3.0+h*60.0);
    col += s*vec3(1.0)*(1.0+u_hat*3.0)*smoothstep(hz+0.02,0.45,p.y);
  }
  // sun
  float sr = 0.36 + 0.035*u_bass + 0.03*u_kick;
  vec2 sc = vec2(0.0, mix(hz-sr-0.06, hz+sr*0.55+0.12, sun));
  float d = length(p-sc);
  float disk = smoothstep(sr, sr-0.012, d)*step(hz,p.y);
  float ky = clamp((p.y-(sc.y-sr))/(2.0*sr),0.0,1.0);
  float slit = smoothstep(0.58,0.0,ky);
  float bandv = fract(p.y*13.0 + u_t*0.12);
  float hole = 1.0-smoothstep(slit*0.8-0.03, slit*0.8+0.03, bandv);
  disk *= 1.0-hole;
  vec3 sunCol = mix(vec3(1.0,0.82,0.22), vec3(1.0,0.10,0.64), smoothstep(0.08,0.95,ky));
  col += pal(0.08,u_pal)*exp(-max(d-sr,0.0)*4.5)*(0.55+0.9*u_bass)*step(hz,p.y)*sun;
  col = mix(col, sunCol*(1.5+0.5*u_kick), disk);
  // city skyline
  float bw = 26.0;
  float bid = floor(p.x*bw);
  float bh = (0.03+0.24*pow(hash11(bid*1.37+3.0),1.6))*(0.55+0.45*smoothstep(0.75,0.0,abs(p.x)))*u_city;
  if(p.y>hz && p.y<hz+bh){
    vec3 b = vec3(0.012,0.0,0.05);
    vec2 wc = vec2(fract(p.x*bw)*4.0, (p.y-hz)*70.0);
    vec2 wid = vec2(floor(wc.x)+bid*7.0, floor(wc.y));
    float lit = step(0.62, hash21(wid)) * step(0.15,fract(wc.x)) * step(fract(wc.x),0.85) * step(0.2,fract(wc.y)) * step(fract(wc.y),0.8);
    lit *= step(0.35, fract(hash21(wid+9.0)*5.0 + u_t*(0.15+0.3*hash21(wid))));
    b += lit*pal(hash21(wid)*0.9, u_pal)*(1.0+u_hat*2.0)*1.1;
    col = b;
  }
  float rim = smoothstep(0.006,0.0,abs(p.y-(hz+bh)))*step(0.001,bh)*step(hz,p.y);
  col += rim*pal(0.55,u_pal)*1.5*u_neon;
  // floor
  if(p.y<hz){
    float dy = hz - p.y;
    float z = 0.30/dy;
    float x = p.x*z*1.3;
    float wz = z*0.9 + dir*u_dist;
    float lz = gline(wz, 0.012);
    float lx = gline(x*0.9+0.5, 0.012);
    float fade = smoothstep(0.0,0.28,dy);
    vec3 base = mix(vec3(0.03,0.0,0.09), pal(0.7,u_pal)*0.12, smoothstep(0.0,0.9,dy));
    vec3 gcol = mix(pal(0.40,u_pal), pal(0.78,u_pal), 0.5+0.5*sin(wz*0.35+x*0.2));
    vec3 f = base + (lz+lx)*gcol*1.15*fade*u_neon*(0.7+1.1*u_bass+0.5*u_kick);
    // lane dashes (tail lights streaming away / towards us)
    float lane = exp(-abs(abs(x)-0.9)*18.0)*step(0.45,fract(wz*0.5))*fade;
    f += lane*mix(vec3(1.0,0.1,0.2), vec3(0.2,0.9,1.0), step(0.0,x))*2.2*u_neon;
    // sun reflection
    f += pal(0.1,u_pal)*exp(-abs(p.x)*2.2)*exp(-dy*3.2)*sun*(0.8+u_bass);
    col = f;
  }
  // horizon glow line
  col += pal(0.2,u_pal)*exp(-abs(p.y-hz)*45.0)*(1.0+u_bass*1.5)*u_neon;
  // gears + floating debris (system failing / gravity lifting)
  if(gearsAmt>0.001){
    float gw = 0.006;
    float g1 = gearShape(p, vec2(-0.20,0.42), 0.30, 14.0, u_t*0.6+u_dist*0.15, gw);
    float g2 = gearShape(p, vec2(0.30,0.14), 0.21, 10.0, -u_t*0.86-u_dist*0.21+0.3, gw);
    float g3 = gearShape(p, vec2(-0.26,-0.05), 0.15, 8.0, u_t*1.1+u_dist*0.3, gw);
    col += gearsAmt*(g1*pal(0.15,u_pal)+g2*pal(0.45,u_pal)+g3*pal(0.75,u_pal))*1.7;
    vec2 g = vec2(p.x*7.0, p.y*7.0 - u_t*0.9*gearsAmt);
    vec2 id = floor(g); float hh = hash21(id);
    vec2 q = (fract(g)-0.5)*rot(hh*6.0+u_t*(hh-0.5)*3.0);
    float sq = smoothstep(0.02,0.0,abs(max(abs(q.x),abs(q.y))-0.22))*step(0.7,hh);
    col += sq*pal(hh,u_pal)*gearsAmt*1.2;
  }
  return col;
}

// ------------------------------------------------------------------ 1: POLYGON TUNNEL
vec3 sceneTunnel(vec2 p, vec4 a){
  float n = a.x, tw = a.y, spin = a.z;
  float r = length(p)+1e-4;
  float ang = atan(p.y,p.x) + spin + tw*log(r+0.6);
  float sector = TAU/n;
  float la = mod(ang+sector*0.5, sector)-sector*0.5;
  float d = r*cos(la);
  float z = 0.5/(d+0.015);
  float wz = z + u_dist;
  float ring = gline(wz*0.7, 0.05);
  float spoke = smoothstep(0.022,0.0,(sector*0.5-abs(la))*r);
  vec2 pc = vec2(la/sector*4.0, wz*0.7);
  float chk = mod(floor(pc.x+8.0)+floor(pc.y),2.0);
  float fog = exp(-r*1.0);
  vec3 c = pal(wz*0.045+la*0.25+0.1, u_pal);
  vec3 col = c*(ring*2.4 + spoke*1.6 + chk*0.22*(0.4+u_rms));
  col *= (0.35+0.65*smoothstep(0.0,0.3,r));
  col += pal(0.3+wz*0.02,u_pal)*exp(-r*5.5)*(1.3+2.2*u_kick);
  return col*(0.7+0.9*u_kick);
}

// ------------------------------------------------------------------ 2: KALI FRACTAL
vec3 sceneKali(vec2 p, vec4 a){
  float t = u_t*0.11 + u_dist*0.012;
  p *= a.x*(1.0+0.14*sin(t*3.0)-0.08*u_kick);
  p = rot(t*0.6+a.y)*p;
  vec2 z = p;
  vec2 c = vec2(0.82+0.12*sin(t*1.7+a.z), 0.58+0.10*cos(t*1.3)) + vec2(0.02*u_wob, -0.015*u_wob);
  float orbit = 1e3, lines = 1e3, ring = 1e3;
  for(int i=0;i<10;i++){
    z = abs(z)/dot(z,z) - c;
    float d2 = dot(z,z);
    orbit = min(orbit, d2);
    lines = min(lines, abs(z.x - 0.5*z.y));
    ring = min(ring, abs(sqrt(d2)-0.7));
  }
  float so = sqrt(orbit);
  vec3 col = pal(0.9+t*0.3, u_pal)*0.02;
  col += pal(0.85+t*0.2, u_pal)*smoothstep(0.05,0.0,so)*1.4;
  col += pal(0.15+t*0.3, u_pal)*smoothstep(0.028,0.0,lines)*1.9;
  col += pal(0.55-t*0.3, u_pal)*smoothstep(0.022,0.0,ring)*1.7;
  col *= 0.75+0.7*u_rms;
  return col;
}

// ------------------------------------------------------------------ 3: MANDALA (spectrum petals + polygons)
float polyD(vec2 p, float n, float rotA){
  float a = atan(p.y,p.x)+rotA; float s = TAU/n;
  return length(p)*cos(mod(a+s*0.5,s)-s*0.5);
}
vec3 sceneMandala(vec2 p, vec4 a){
  float N = a.x;
  float r = length(p);
  float ang = atan(p.y,p.x) + a.y + u_t*0.08;
  float sa = TAU/N;
  float fa = abs(mod(ang,sa)-sa*0.5);
  float idx = fa/(sa*0.5);
  vec3 col = vec3(0.0);
  float bars = 20.0;
  float bi = floor(idx*bars); float bf = fract(idx*bars);
  float s = specAt((bi+0.5)/bars);
  float rb = 0.16, len = 0.08 + 0.62*s*(0.6+0.8*u_kick*0.0+0.6);
  float bw = smoothstep(0.0,0.12,bf)*smoothstep(1.0,0.88,bf);
  float inside = smoothstep(rb+len+0.012, rb+len-0.012, r)*smoothstep(rb-0.01, rb+0.01, r)*bw;
  vec3 pc = pal(r*1.4+idx*0.35+u_t*0.07, u_pal);
  col += pc*inside*(0.55+0.5*s);
  col += pal(idx*0.6+0.5,u_pal)*exp(-abs(r-(rb+len))*70.0)*bw*1.6;
  for(int i=0;i<5;i++){
    float fi = float(i);
    float rad = 0.12+0.17*fi + 0.025*sin(u_t*2.0+fi) + 0.05*u_kick;
    float dd = polyD(p, 3.0+fi, (mod(fi,2.0)<0.5?1.0:-1.0)*u_t*0.35 + fi);
    float ring = smoothstep(0.011,0.0,abs(dd-rad));
    col += pal(fi*0.21+u_t*0.05,u_pal)*ring*(1.2+u_hat*1.5);
  }
  col += pal(0.1+u_t*0.1,u_pal)*exp(-r*9.0)*(1.0+2.0*u_kick);
  return col;
}

// ------------------------------------------------------------------ 4: HEX GRID
float hexDist(vec2 p){ p = abs(p); float c = dot(p, normalize(vec2(1.0,1.73))); return max(c,p.x); }
vec3 sceneHex(vec2 p, vec4 a){
  p = rot(a.y)*p*a.x;
  vec2 rr = vec2(1.0,1.73); vec2 h = rr*0.5;
  vec2 ga = mod(p,rr)-h; vec2 gb = mod(p-h,rr)-h;
  vec2 gv = dot(ga,ga)<dot(gb,gb)? ga : gb;
  vec2 id = p-gv;
  float edgeD = 0.5-hexDist(gv);
  float cd = length(id);
  float wave = 0.5+0.5*sin(cd*1.35 - u_dist*0.9 + a.z);
  float fl = smoothstep(0.35,0.75,wave + 0.45*u_kick);
  float edge = smoothstep(0.05,0.0,edgeD);
  float cell = smoothstep(0.0,0.35,edgeD);
  vec3 c = pal(cd*0.07+u_t*0.08+hash21(id)*0.25, u_pal);
  vec3 col = c*(edge*1.8 + fl*cell*1.1) + c*0.06;
  col += vec3(1.0)*fl*smoothstep(0.38,0.5,edgeD)*0.5*u_hat;
  return col*(0.8+0.8*u_kick);
}

// ------------------------------------------------------------------ 5: VORTEX (log spiral)
vec3 sceneVortex(vec2 p, vec4 a){
  float r = length(p)+1e-4;
  float ang = atan(p.y,p.x);
  float s = ang/TAU*a.x + log(r)*a.y - u_dist*0.3;
  float idx = floor(s); float band = fract(s);
  float w = smoothstep(0.0,0.08,band)*smoothstep(0.62,0.5,band);
  vec3 c1 = pal(0.1+idx*0.11+u_t*0.04, u_pal);
  vec3 c2 = pal(0.62+idx*0.11, u_pal)*0.12;
  vec3 col = mix(c2, c1*1.7, w);
  col *= smoothstep(0.0,0.12,r);
  col += pal(0.4,u_pal)*exp(-r*7.0)*(1.2+2.0*u_kick);
  col += c1*smoothstep(0.03,0.0,abs(band-0.5))*0.6;
  return col*(0.8+0.8*u_kick);
}

// ------------------------------------------------------------------ 6: LIQUID contours
vec3 sceneLiquid(vec2 p, vec4 a){
  vec2 q = p*a.x;
  float t = u_t*0.22 + u_dist*0.015;
  float amp = 0.40 + 1.0*u_wob;
  for(int i=0;i<5;i++){
    float fi = float(i);
    q += amp*vec2(sin(q.y*1.7+t*(1.0+0.3*fi)+fi), cos(q.x*1.9-t*1.2+fi*1.7));
    q = rot(0.35)*q;
  }
  float f = 0.5+0.5*sin(q.x*1.3)*cos(q.y*1.1);
  float band = fract(f*6.0 - t*0.6);
  float line = smoothstep(0.1,0.0,band) + smoothstep(0.9,1.0,band);
  vec3 col = pal(f*0.9+t*0.1,u_pal)*(0.10+0.35*f) + pal(f*0.9+0.4+t*0.1,u_pal)*line*1.6;
  return col*(0.8+0.8*u_kick);
}

vec3 evalScene(int id, vec2 p, vec4 a){
  if(id==0) return sceneOutrun(p,a);
  if(id==1) return sceneTunnel(p,a);
  if(id==2) return sceneKali(p,a);
  if(id==3) return sceneMandala(p,a);
  if(id==4) return sceneHex(p,a);
  if(id==5) return sceneVortex(p,a);
  return sceneLiquid(p,a);
}

// ------------------------------------------------------------------ glass shatter (voronoi)
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

KAL = "#version 330\n" + COMMON + """
uniform vec2 u_res;
uniform sampler2D u_tex;
uniform float u_seg, u_krot, u_kzoom, u_kphase, u_mirx, u_mirror_y;
uniform vec2 u_kc;
in vec2 uv;
out vec4 fragColor;
void main(){
  float asp = u_res.x/u_res.y;
  vec2 p = (uv-0.5)*vec2(asp,1.0)*2.0;
  p = (p-u_kc)/u_kzoom;
  if(u_seg>1.5){
    float r = length(p); float a = atan(p.y,p.x)+u_krot;
    float sa = TAU/u_seg;
    a = mod(a,sa); a = abs(a-sa*0.5);
    a += u_kphase;
    p = r*vec2(cos(a),sin(a));
  }
  if(u_mirx>0.5) p.x = abs(p.x);
  if(u_mirror_y>0.5) p.y = abs(p.y);
  vec2 q = p/(vec2(asp,1.0)*2.0)+0.5;
  q = 1.0-abs(1.0-mod(q,2.0));
  fragColor = texture(u_tex, q);
}
"""

FB = "#version 330\n" + COMMON + """
uniform vec2 u_res;
uniform sampler2D u_new, u_prev;
uniform float u_decay, u_fzoom, u_frot, u_fhue, u_fmix;
uniform vec2 u_fshift;
in vec2 uv;
out vec4 fragColor;
void main(){
  float asp = u_res.x/u_res.y;
  vec2 p = (uv-0.5)*vec2(asp,1.0)*2.0;
  vec2 q = rot(u_frot)*p/u_fzoom + u_fshift;
  vec2 uvp = q/(vec2(asp,1.0)*2.0)+0.5;
  vec3 prev = texture(u_prev, uvp).rgb;
  if(abs(u_fhue)>0.0001) prev = hueShift(prev, u_fhue);
  prev *= u_decay;
  vec3 nw = texture(u_new, uv).rgb;
  vec3 o = max(nw, prev) + u_fmix*0.22*min(nw, prev);
  o = min(o, vec3(5.0));
  fragColor = vec4(o,1.0);
}
"""

BRIGHT = "#version 330\n" + """
uniform sampler2D u_tex; uniform float u_thr;
in vec2 uv; out vec4 fragColor;
void main(){
  vec3 c = texture(u_tex, uv).rgb;
  float l = max(max(c.r,c.g),c.b);
  float k = smoothstep(u_thr, u_thr+0.7, l);
  fragColor = vec4(c*k,1.0);
}
"""

BLUR = "#version 330\n" + """
uniform sampler2D u_tex; uniform vec2 u_dir;   // texel step in uv units
in vec2 uv; out vec4 fragColor;
void main(){
  vec3 s = texture(u_tex, uv).rgb*0.2270270270;
  s += (texture(u_tex, uv+u_dir*1.3846153846).rgb + texture(u_tex, uv-u_dir*1.3846153846).rgb)*0.3162162162;
  s += (texture(u_tex, uv+u_dir*3.2307692308).rgb + texture(u_tex, uv-u_dir*3.2307692308).rgb)*0.0702702703;
  fragColor = vec4(s,1.0);
}
"""

POST = "#version 330\n" + COMMON + """
uniform vec2 u_res;
uniform sampler2D u_comp, u_b1, u_b2, u_b3, u_b4, u_text;
uniform float u_t, u_bloom, u_ca, u_glit, u_flash, u_inv, u_black, u_fade, u_scan, u_grain, u_vig, u_pump, u_crt, u_dot, u_expo, u_sat, u_capdim;
uniform vec3 u_flashcol;
uniform vec2 u_shake;
in vec2 uv;
out vec4 fragColor;
vec3 aces(vec3 x){ return clamp((x*(2.51*x+0.03))/(x*(2.43*x+0.59)+0.14),0.0,1.0); }
void main(){
  float asp = u_res.x/u_res.y;
  vec2 c0 = uv-0.5;
  // CRT shutdown (u_crt: 0..1)
  float crtMask = 1.0;
  if(u_crt>0.0){
    float ph1 = clamp(u_crt/0.55,0.0,1.0), ph2 = clamp((u_crt-0.55)/0.35,0.0,1.0);
    float sy = mix(1.0, 0.004, ph1*ph1*(3.0-2.0*ph1));
    float sx = mix(1.0, 0.0, ph2);
    c0.y /= sy; c0.x /= max(sx,0.0005);
    if(abs(c0.y)>0.5 || abs(c0.x)>0.5) crtMask = 0.0;
  }
  c0 /= (1.0+u_pump);
  vec2 q = c0+0.5+u_shake;
  // glitch: horizontal block displacement
  float blk = floor(q.y*38.0);
  float gr = hash21(vec2(blk, floor(u_t*24.0)));
  float gon = step(1.0-0.55*u_glit, gr);
  q.x += gon*(hash21(vec2(blk,floor(u_t*24.0)+7.0))-0.5)*0.16*u_glit;
  vec2 dir = (q-0.5); float rr = length(dir*vec2(asp,1.0));
  vec2 off = dir*(u_ca*(0.4+rr*1.6));
  float cr = texture(u_comp, q+off).r, cg = texture(u_comp, q).g, cb = texture(u_comp, q-off).b;
  vec3 c = vec3(cr,cg,cb);
  // bloom
  vec3 bl = texture(u_b1,q).rgb*0.30 + texture(u_b2,q).rgb*0.22 + texture(u_b3,q).rgb*0.17 + texture(u_b4,q).rgb*0.12;
  c += bl*u_bloom;
  // darken a band behind the lyric captions for legibility
  c *= 1.0 - u_capdim*0.55*exp(-pow((uv.y-0.307)/0.075,2.0));
  // flash / invert
  c += u_flashcol*u_flash;
  c = mix(c, vec3(1.15)-c, u_inv);
  // lyric captions: separate crisp layer + soft neon glow (not inverted, not dimmed)
  vec4 tx = texture(u_text, q);
  vec2 px = 1.0/u_res;
  vec3 tg = vec3(0.0);
  for(int k=0;k<8;k++){
    float a = float(k)*0.7853982;
    tg += texture(u_text, q+vec2(cos(a),sin(a))*px*9.0).rgb;
    tg += texture(u_text, q+vec2(cos(a),sin(a))*px*22.0).rgb*0.6;
  }
  c = c*(1.0-tx.a) + tx.rgb + tg*0.07;
  c = max(c-vec3(0.02), 0.0);
  c *= u_expo;
  float lum = dot(c,vec3(0.299,0.587,0.114));
  c = mix(vec3(lum), c, u_sat);
  c = aces(c);
  c = pow(c, vec3(0.92));
  // scanlines + vignette + grain
  c *= 1.0-u_scan*(0.5+0.5*sin(q.y*u_res.y*3.14159));
  float vg = 1.0-u_vig*pow(length((uv-0.5)*vec2(1.0,1.15))*1.35,2.2);
  c *= clamp(vg,0.0,1.0);
  c += (hash21(uv*u_res+fract(u_t)*91.0)-0.5)*u_grain;
  // singularity dot
  c += vec3(1.0)*u_dot*smoothstep(0.02+0.2*u_dot,0.0,length((uv-0.5)*vec2(asp,1.0)));
  c *= u_fade*(1.0-u_black)*crtMask;
  if(u_crt>0.0) c += vec3(0.8,0.9,1.0)*crtMask*smoothstep(0.3,0.0,abs(c0.y))*u_crt*0.6;
  fragColor = vec4(clamp(c,0.0,1.0),1.0);
}
"""

TEXT_V = """
#version 330
in vec2 pos;
uniform vec2 u_res, u_center, u_size;
uniform float u_rot;
out vec2 tuv;
void main(){
  tuv = pos*0.5+0.5; tuv.y = 1.0-tuv.y;
  vec2 q = pos*u_size*0.5;
  float c=cos(u_rot), s=sin(u_rot);
  q = vec2(c*q.x - s*q.y, s*q.x + c*q.y);
  vec2 px = u_center + vec2(q.x, -q.y);
  gl_Position = vec4(px/u_res*2.0-1.0, 0.0, 1.0);
  gl_Position.y = -gl_Position.y;
}
"""

TEXT_F = """
#version 330
uniform sampler2D u_tex;
uniform float u_alpha, u_split, u_add;
uniform vec3 u_tint;
in vec2 tuv; out vec4 fragColor;
void main(){
  float sp = u_split/ float(textureSize(u_tex,0).x);
  vec4 a = texture(u_tex, tuv);
  vec4 r = texture(u_tex, tuv+vec2(sp,0.0));
  vec4 b = texture(u_tex, tuv-vec2(sp,0.0));
  vec3 rgb = vec3(r.r, a.g, b.b);
  float al = max(a.a, max(r.a,b.a));
  fragColor = vec4(rgb*u_tint, al)*u_alpha;
}
"""
