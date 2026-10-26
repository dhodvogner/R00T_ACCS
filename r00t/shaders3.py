"""GLSL v3: 3D roadside palms, terminal EQ, hyperspace warp, spin-blur camera, full-screen ASCII pass, new post FX."""
from .shaders import VERT, COMMON, FB, BRIGHT, BLUR, TEXT_V, TEXT_F  # noqa: F401
from .shaders2 import SCENE2, SPRITE_V, SPRITE_F  # noqa: F401


def _sub(src, old, new):
    assert old in src, old[:60]
    return src.replace(old, new, 1)


# ---------------------------------------------------------------------------- scene
SCENE3 = SCENE2
SCENE3 = _sub(SCENE3, "uniform sampler2D u_spec, u_rain;",
              "uniform sampler2D u_spec, u_rain, u_atlas;\nuniform vec4 u_palm0, u_palm1, u_palm2;\nuniform float u_dim, u_wdist, u_shB, u_gt;")
SCENE3 = _sub(SCENE3, "    float wz = z*0.9+dir*u_dist;", "    float wz = z*0.9+u_wdist;")
SCENE3 = _sub(SCENE3, "    float lz = gline(wz,0.012)*(1.0-drop);", "    float lz = mix(gline(wz,0.012), 0.03, smoothstep(0.35,0.9,fwidth(wz)))*(1.0-drop);")
SCENE3 = _sub(SCENE3, "vec3 cb = evalScene(u_sB, ps, u_aB);", "vec3 cb = evalScene(u_sB, (u_shB>0.5)?p:ps, u_aB);")
SCENE3 = _sub(SCENE3, "  col += edge*u_shatter*vec3(1.0,0.92,1.0)*2.4;\n  fragColor = vec4(col,1.0);",
              "  col *= u_dim;\n  col += edge*u_shatter*vec3(1.0,0.92,1.0)*2.4;\n  fragColor = vec4(col,1.0);")

PALMS = """
// ------------------------------------------------------------------ 3D roadside palm billboards
float palmAlpha(vec2 q, vec4 rect){
  if(q.x<0.0||q.x>1.0||q.y<0.0||q.y>1.0) return 0.0;
  return texture(u_atlas, (rect.xy+q*rect.zw)/4096.0).a;
}
void palms(vec2 p, float hz, float dir, float hack, out float outA, out float outZ){
  outA = 0.0; outZ = 1e9;
  for(int i=0;i<8;i++){
    for(int s=0;s<2;s++){
      float side = (s==0)?-1.0:1.0;
      float seed = float(i)*1.7+float(s)*5.3;
      float wz = float(i)*0.95+hash11(seed)*0.5;
      float z = mod(wz/0.9 - u_wdist/0.9, 7.6)+0.33;
      float X = side*(0.50+0.55*hash11(seed+2.1));
      float sc = 0.30/z;
      float baseY = hz - sc;
      float hh = 2.7*sc*(0.85+0.45*hash11(seed+4.4));
      float vsel = hash11(seed+7.7)*3.0;
      vec4 r = (vsel<1.0)?u_palm0:((vsel<2.0)?u_palm1:u_palm2);
      float asp = r.z/r.w;
      float cx = X/(z*1.3) + 0.012*hh*sin(u_t*0.9+seed) + 0.01*hh*u_kick*sin(u_t*40.0+seed);
      vec2 q = vec2((p.x-cx)/(hh*asp)+0.5, 1.0-(p.y-baseY)/hh);
      if(side>0.0) q.x = 1.0-q.x;
      float a = palmAlpha(q, r);
      if(hack>0.0){
        vec2 cell = floor(vec2(q.x*14.0, q.y*24.0)) + float(i)*3.0;
        if(hash21(cell+floor(u_t*9.0)+side) < hack*0.55*step(0.0,q.x)) a = 0.0;
      }
      if(a>0.5 && z<outZ){ outA=a; outZ=z; }
    }
  }
}
"""
SCENE3 = _sub(SCENE3, "// ------------------------------------------------------------------ 0: RETRO WORLD",
              PALMS + "\n// ------------------------------------------------------------------ 0: RETRO WORLD")
SCENE3 = _sub(SCENE3, "  // hack tint: pull everything toward cyan/white terminal look",
              """  { float pa, pz; palms(p, hz, dir, h, pa, pz);
    if(pa>0.5){
      vec3 pc = vec3(0.022,0.0,0.065);
      pc += mix(PINK,CYAN,0.3)*0.10*smoothstep(0.2,0.0,abs(fract(pz*0.5)-0.5));
      pc = mix(pc, vec3(0.50,0.11,0.38), smoothstep(2.2,7.6,pz));
      col = pc;
    }
  }
  // hack tint: pull everything toward cyan/white terminal look""")

NEW_SCENES = """
// ------------------------------------------------------------------ 5: TERMINAL EQUALIZER (gets turned into code by the ASCII pass)
vec3 sceneTermEQ(vec2 p, vec4 a){
  float nb = 34.0;
  float x = p.x/(0.5625*2.0)+0.5;
  float bi = floor(x*nb), bf = fract(x*nb);
  float s = specAt((bi+0.5)/nb);
  float hgt = 0.08+0.78*pow(s,1.2)*(0.8+0.5*u_kick);
  float gap = smoothstep(0.0,0.12,bf)*smoothstep(1.0,0.88,bf);
  vec3 col = vec3(0.0);
  for(int m=0;m<2;m++){
    float y = (m==0)? p.y+1.0 : 1.0-p.y;
    float hh = (m==0)? hgt : hgt*0.6;
    float seg = smoothstep(0.0,0.12,fract(y*16.0))*smoothstep(1.0,0.88,fract(y*16.0));
    float bar = step(y,hh)*gap*mix(1.0,seg,0.6);
    vec3 c = pal(bi/nb + y*0.35 + u_t*0.05, u_pal);
    col += c*bar*1.5;
    col += vec3(1.0)*step(abs(y-hh),0.022)*gap*1.8;
  }
  col += pal(0.1,u_pal)*exp(-abs(p.y)*1.4)*0.10;
  return col;
}

// ------------------------------------------------------------------ 6: HYPERSPACE (3D streaks flying past the camera)
vec3 sceneWarp(vec2 p, vec4 a){
  float r = length(p), ang = atan(p.y,p.x);
  vec3 col = vec3(0.0);
  for(int l=0;l<3;l++){
    float fl = float(l);
    float nang = 90.0+70.0*fl;
    float ai = floor(ang/TAU*nang);
    float hh = hash21(vec2(ai, fl*13.0));
    float aw = fract(ang/TAU*nang);
    float lw = smoothstep(0.10,0.0,abs(aw-0.5));
    float z = fract(hh + u_dist*(0.05+0.035*fl));
    float rs = z*z*1.9;
    float len = 0.04+0.6*z*z;
    float on = smoothstep(rs-len,rs,r)*smoothstep(rs+0.012,rs,r);
    vec3 c = mix(pal(hh,u_pal), vec3(1.0), 0.35);
    col += c*lw*on*(0.8+1.8*z)*(0.55+u_rms);
  }
  col += pal(0.1,u_pal)*exp(-r*6.0)*(0.5+1.6*u_kick);
  return col*((a.w>0.01)?a.w:1.0);
}


// ------------------------------------------------------------------ 7: CRYSTAL GLASS CATHEDRAL (raymarched KIFS diamond lattice; adapted from the supplied shader)
float gOcta(vec3 p, float s){ p=abs(p); return (p.x+p.y+p.z-s)*0.57735027; }
vec3 gPal(float t){ return pal(fract(t), u_pal)*0.85+0.15; }
float gMap(vec3 p, out vec4 trap){
  float scale = 1.0;
  trap = vec4(abs(p),0.0);
  float t = u_gt*0.05;
  vec3 fo = vec3(0.48,0.62,0.35)*(0.935+0.10*u_bass) + vec3(sin(t)*0.05, cos(t*1.1)*0.05, 0.0);
  for(int i=0;i<5;i++){
    p = abs(p)-fo;
    p.xy *= rot(0.3+float(i)*0.1);
    p.xz *= rot(0.25-float(i)*0.08);
    p = clamp(p,-1.0,1.0)*2.0-p;
    float r2 = dot(p,p);
    float k = max(1.25/clamp(r2,0.15,1.0),0.8);
    p *= k; scale *= k;
    trap = min(trap, vec4(abs(p),r2));
  }
  return 0.55*gOcta(p,1.3)/scale;
}
vec3 gNormal(vec3 p){
  vec2 e = vec2(0.0005,-0.0005); vec4 d;
  return normalize(e.xyy*gMap(p+e.xyy,d)+e.yyx*gMap(p+e.yyx,d)+e.yxy*gMap(p+e.yxy,d)+e.xxx*gMap(p+e.xxx,d));
}
vec3 gEnv(vec3 r){
  vec3 col = mix(vec3(0.12,0.02,0.26), vec3(0.01,0.0,0.05), abs(r.y));
  float hg = pow(1.0-abs(r.y),4.0);
  col += vec3(1.0,0.25,0.6)*hg*0.8;
  vec3 pp = r*25.0; vec3 ip = floor(pp);
  float sn = fract(sin(dot(ip,vec3(12.9898,78.233,37.719)))*43758.5453);
  col += vec3(smoothstep(0.975,1.0,sn)*(0.3+0.7*sin(u_t*4.0+sn*8.0))*0.8);
  vec3 sd = normalize(vec3(1.0,1.5,-2.0));
  col += vec3(1.0,0.78,0.45)*pow(max(dot(r,sd),0.0),64.0)*2.0;
  float lines = smoothstep(0.985,1.0,sin(r.y*40.0+r.x*20.0));
  col += vec3(0.0,0.9,1.0)*lines*(1.0-abs(r.y))*0.9;
  return col;
}
vec3 sceneGlass(vec2 p, vec4 a){
  vec2 uvg = p*0.5;
  float t = a.x;
  float chroma = 0.087 + a.w;
  float refl = 10.85;
  vec3 ro = vec3(0.0,0.0,-1.8-(5.575+a.y)*0.5);
  vec3 rd = normalize(vec3(uvg,1.25));
  float cax = t*0.07, cay = t*0.03;
  ro.yz *= rot(cay); ro.xz *= rot(cax);
  rd.yz *= rot(cay); rd.xz *= rot(cax);
  float td = 0.0; bool hit = false; vec4 ft = vec4(0.0);
  for(int i=0;i<80;i++){
    vec3 pos = ro+rd*td; vec4 ct;
    float d = gMap(pos,ct);
    if(d<0.0012){ hit = true; ft = ct; break; }
    td += d*0.65;
    if(td>6.0) break;
  }
  vec3 fc = vec3(0.0);
  if(hit){
    vec3 ip = ro+rd*td;
    vec3 n = gNormal(ip);
    vec3 rf = reflect(rd,n);
    float tr = 0.015; bool rh = false; vec4 rt; vec3 rp;
    for(int j=0;j<36;j++){
      rp = ip+rf*tr;
      float d = gMap(rp,rt);
      if(d<0.0012){ rh = true; break; }
      tr += d*0.7;
      if(tr>3.5) break;
    }
    vec3 refc = vec3(0.0);
    if(rh){
      vec3 rn = gNormal(rp);
      float df = max(dot(rn,normalize(vec3(0.5,0.8,-0.6))),0.0);
      refc = gPal(rt.w*0.25+t*0.1)*(df*0.7+0.3) + vec3(0.15,0.25,0.35);
    } else {
      refc.r = gEnv(rf+vec3(chroma*0.05,0.0,0.0)).r;
      refc.g = gEnv(rf).g;
      refc.b = gEnv(rf-vec3(chroma*0.05,0.0,0.0)).b;
    }
    vec3 fr = refract(rd,n,1.0/1.45);
    if(dot(fr,fr)<0.1) fr = rf;
    vec3 trc = vec3(0.0);
    trc.r = gEnv(fr+vec3(chroma*0.03,0.0,0.0)).r;
    trc.g = gEnv(fr).g;
    trc.b = gEnv(fr-vec3(chroma*0.03,0.0,0.0)).b;
    trc *= gPal(ft.w*0.18+t*0.05)*0.5+vec3(0.5);
    float fres = 0.05+0.95*pow(1.0-max(dot(-rd,n),0.0),5.0);
    fres = clamp(fres*refl*1.5,0.0,1.0);
    fc = mix(trc,refc,fres);
    vec3 ld = normalize(vec3(1.0,1.5,-2.0));
    vec3 hv = normalize(ld-rd);
    fc += vec3(pow(max(dot(n,hv),0.0),128.0)*1.2*refl);
    fc *= exp(-td*0.15);
  } else {
    fc = gEnv(rd);
  }
  fc = pow(max(fc,vec3(0.0)), vec3(1.45));
  return fc*(0.85+0.6*u_kick);
}

vec3 evalScene(int id, vec2 p, vec4 a){"""
SCENE3 = _sub(SCENE3, "vec3 evalScene(int id, vec2 p, vec4 a){", NEW_SCENES)
SCENE3 = _sub(SCENE3, "  return sceneVoid(p,a);\n}",
              "  if(id==5) return sceneTermEQ(p,a);\n  if(id==6) return sceneWarp(p,a);\n  if(id==7) return sceneGlass(p,a);\n  return sceneVoid(p,a);\n}")

# ---------------------------------------------------------------------------- camera: roll + rotational/zoom motion blur (+ kaleido)
KAL3 = "#version 330\n" + COMMON + """
uniform vec2 u_res;
uniform sampler2D u_tex;
uniform float u_seg, u_krot, u_kzoom, u_kphase, u_mirx, u_mirror_y, u_roll, u_blr, u_blz, u_fov;
uniform vec2 u_kc;
in vec2 uv;
out vec4 fragColor;
vec3 samp(vec2 p0, float roll, float zoom){
  float asp = u_res.x/u_res.y;
  vec2 p = rot(roll)*p0/zoom;
  p = p/(1.0+u_fov*dot(p,p));
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
  return texture(u_tex,q).rgb;
}
void main(){
  float asp = u_res.x/u_res.y;
  vec2 p0 = (uv-0.5)*vec2(asp,1.0)*2.0 - u_kc;
  vec3 acc = vec3(0.0);
  float n = 1.0;
  if(u_blr>0.0005 || u_blz>0.0005){
    n = 14.0;
    for(int i=0;i<14;i++){
      float f = float(i)/13.0-0.5;
      acc += samp(p0, u_roll+f*u_blr, u_kzoom*(1.0+f*u_blz));
    }
  } else {
    acc = samp(p0, u_roll, u_kzoom);
  }
  fragColor = vec4(acc/n,1.0);
}
"""

# ---------------------------------------------------------------------------- full-screen ASCII pass (second rendering pass)
ASCII = "#version 330\n" + COMMON + """
uniform sampler2D u_src, u_glyph;
uniform vec2 u_res;
uniform float u_t, u_amt, u_cell, u_melt, u_cm, u_glyphN, u_jit, u_bright, u_kt, u_ringw, u_flick, u_dir, u_blob;
uniform vec3 u_acol;
in vec2 uv;
out vec4 fragColor;
float vn(vec2 p){ vec2 i=floor(p), f=fract(p); f=f*f*(3.0-2.0*f);
  return mix(mix(hash21(i),hash21(i+vec2(1,0)),f.x), mix(hash21(i+vec2(0,1)),hash21(i+vec2(1,1)),f.x), f.y); }
void main(){
  vec2 px = uv*u_res;
  vec2 cs = vec2(floor(u_cell*0.56), u_cell);
  vec2 cell = floor(px/cs);
  // kick shockwave: a ring that sweeps outward and turns pixels into code
  float rr = length((px-u_res*0.5)/u_res.y);
  float ringR = u_kt*1.7;
  float ring = smoothstep(u_ringw,0.0,abs(rr-ringR))*step(u_kt,0.75);
  // melting / falling code: columns slide downward at different speeds
  float colh = hash11(cell.x*1.37+3.0);
  float drip = u_melt*(0.3+2.4*colh)*(0.6+0.4*sin(u_t*3.0+colh*20.0));
  float blob = vn(cell*0.07+vec2(u_t*0.25,-u_t*0.18))*0.6 + vn(cell*0.21+vec2(-u_t*0.1,u_t*0.13))*0.4;
  float rnd = mix(hash21(cell+floor(u_t*12.0)), blob, u_blob)*0.92;
  float amt = clamp(u_amt+ring*0.95, 0.0, 1.0);
  float on = step(rnd, amt);
  vec2 sc = cell+vec2(0.0, drip*u_dir);
  vec2 suv = (sc+0.5)*cs/u_res;
  vec2 st = vec2(0.0, cs.y/u_res.y*0.3);
  vec3 c = (texture(u_src,suv).rgb + texture(u_src,suv+st).rgb + texture(u_src,suv-st).rgb)/3.0;
  float lum = clamp(dot(c,vec3(0.2126,0.7152,0.0722))*u_bright,0.0,1.0);
  float jit = (hash21(cell*1.7+floor(u_t*20.0))-0.5)*u_jit*10.0;
  float gi = clamp(floor(lum*(u_glyphN-1.0)+jit+0.5),0.0,u_glyphN-1.0);
  vec2 f = fract(px/cs);
  float gm = texture(u_glyph, vec2((gi+f.x)/u_glyphN, 1.0-f.y)).r;
  vec3 hue = c/(max(max(c.r,c.g),c.b)+0.001);
  vec3 col = mix(hue, u_acol, u_cm);
  vec3 asc = col*gm*(0.55+1.6*lum)*step(0.015,lum);
  asc += c*mix(0.30, 0.06, u_cm);
  vec3 orig = texture(u_src, uv+vec2(0.0, drip*cs.y/u_res.y*u_dir)).rgb;
  vec3 o = mix(orig, asc, on);
  o += step(0.992,hash21(cell+floor(u_t*30.0)))*u_flick*u_acol;
  fragColor = vec4(o,1.0);
}
"""

# ---------------------------------------------------------------------------- post v3 (+ oscillating chromatic aberration, simplex line glitch, wub flicker)
SNOISE = """
vec3 mod289(vec3 x){ return x-floor(x*(1.0/289.0))*289.0; }
vec2 mod289(vec2 x){ return x-floor(x*(1.0/289.0))*289.0; }
vec3 permute(vec3 x){ return mod289(((x*34.0)+1.0)*x); }
float snoise(vec2 v){
  const vec4 C = vec4(0.211324865405187,0.366025403784439,-0.577350269189626,0.024390243902439);
  vec2 i = floor(v+dot(v,C.yy)); vec2 x0 = v-i+dot(i,C.xx);
  vec2 i1 = (x0.x>x0.y)? vec2(1.0,0.0):vec2(0.0,1.0);
  vec4 x12 = x0.xyxy+C.xxzz; x12.xy -= i1;
  i = mod289(i);
  vec3 p = permute(permute(i.y+vec3(0.0,i1.y,1.0))+i.x+vec3(0.0,i1.x,1.0));
  vec3 m = max(0.5-vec3(dot(x0,x0),dot(x12.xy,x12.xy),dot(x12.zw,x12.zw)),0.0);
  m = m*m; m = m*m;
  vec3 x = 2.0*fract(p*C.www)-1.0; vec3 h = abs(x)-0.5; vec3 ox = floor(x+0.5); vec3 a0 = x-ox;
  m *= 1.79284291400159-0.85373472095314*(a0*a0+h*h);
  vec3 g; g.x = a0.x*x0.x+h.x*x0.y; g.yz = a0.yz*x12.xz+h.yz*x12.yw;
  return 130.0*dot(m,g);
}
"""
POST3 = "#version 330\n" + COMMON + SNOISE + """
uniform vec2 u_res;
uniform sampler2D u_comp, u_b1, u_b2, u_b3, u_b4, u_text, u_mask;
uniform float u_win, u_s;
uniform float u_t, u_bloom, u_ca, u_glit, u_flash, u_inv, u_black, u_fade, u_scan, u_grain, u_vig, u_pump, u_crt, u_dot, u_expo, u_sat, u_capdim;
uniform float u_vhs, u_pix, u_roll, u_tilt, u_caosc, u_glit2;
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
  if(u_vhs>0.0){
    float bot = 1.0-smoothstep(0.0,0.07,uv.y);
    q.x += bot*u_vhs*0.05*(hash11(floor(uv.y*180.0)+floor(u_t*30.0))-0.5);
    float ty = fract(u_t*0.11+0.3);
    float tb = smoothstep(0.03,0.0,abs(uv.y-ty));
    q.x += tb*u_vhs*0.04*(hash11(floor(uv.y*220.0)+floor(u_t*40.0))-0.5)*2.0;
    q.x += u_vhs*0.0015*sin(uv.y*900.0+u_t*60.0);
  }
  // simplex-noise line glitch (big rolling tears + small constant ripples)
  float gnoise = 0.0;
  if(u_glit2>0.0){
    float tm = u_t*2.0;
    gnoise = max(0.0, snoise(vec2(tm, uv.y*0.3))-0.3)*(1.0/0.7);
    gnoise += (snoise(vec2(tm*10.0, uv.y*2.4))-0.5)*0.15;
    gnoise *= u_glit2;
    q.x -= gnoise*gnoise*0.25;
  }
  if(u_pix>0.001){
    float blk = mix(1.0, 56.0*u_s, u_pix);
    q = (floor(q*u_res/blk)+0.5)*blk/u_res;
  }
  float bl = floor(q.y*38.0);
  float gr = hash21(vec2(bl, floor(u_t*24.0)));
  float gon = step(1.0-0.55*u_glit, gr);
  q.x += gon*(hash21(vec2(bl,floor(u_t*24.0)+7.0))-0.5)*0.16*u_glit;
  vec2 dir = (q-0.5); float rr = length(dir*vec2(asp,1.0));
  vec2 off = dir*(u_ca*(0.4+rr*1.6));
  // oscillating chromatic aberration (stacked sines, cubed -> sudden spikes)
  float am = (1.0+sin(u_t*6.0))*0.5;
  am *= 1.0+sin(u_t*16.0)*0.5; am *= 1.0+sin(u_t*19.0)*0.5; am *= 1.0+sin(u_t*27.0)*0.5;
  am = pow(am,3.0)*0.05*u_caosc;
  off += vec2(am+gnoise*0.05, 0.0);
  float cr = texture(u_comp, q+off).r, cg = texture(u_comp, q).g, cb = texture(u_comp, q-off).b;
  vec3 c = vec3(cr,cg,cb);
  c = mix(c, vec3(rand11(uv.y*u_t)), clamp(gnoise,0.0,1.0)*0.3);
  if(mod(floor(gl_FragCoord.y*0.25),2.0)==0.0) c *= 1.0-0.15*clamp(gnoise,0.0,1.0);
  vec3 bl_ = texture(u_b1,q).rgb*0.30 + texture(u_b2,q).rgb*0.22 + texture(u_b3,q).rgb*0.17 + texture(u_b4,q).rgb*0.12;
  c += bl_*u_bloom;
  c *= 1.0 - u_capdim*0.55*exp(-pow((uv.y-0.307)/0.075,2.0));
  c += u_flashcol*u_flash;
  c = mix(c, vec3(1.15)-c, u_inv);
  vec4 mk = texture(u_mask, q);
  c = mix(c, vec3(1.12)-c*0.9, clamp(mk.r,0.0,1.0));
  c = mix(c*(1.0-u_win), c*1.25, clamp(mk.g,0.0,1.0));
  vec4 tx = texture(u_text, q);
  vec2 px = 1.0/u_res;
  vec3 tg = vec3(0.0);
  for(int k=0;k<8;k++){
    float a = float(k)*0.7853982;
    tg += texture(u_text, q+vec2(cos(a),sin(a))*px*9.0*u_s*1.7778).rgb;
    tg += texture(u_text, q+vec2(cos(a),sin(a))*px*22.0*u_s*1.7778).rgb*0.6;
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
""".replace("rand11(uv.y*u_t)", "fract(sin(uv.y*u_t*78.233)*43758.5453)")
