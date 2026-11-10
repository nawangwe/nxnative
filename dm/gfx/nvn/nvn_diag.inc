// Local diagnostics (fork nawangwe/nxnative, branch "diagnostics"; not meant for upstream). State and the DM_CTL commands that only arm something; the bodies that need later
// parts of nvn_mtl.m are in nvn_diag_tail.inc, included at the end of it. Included by nvn_mtl.m after g_cur_frame. Every hook in nvn_mtl.m / nvn_geometry.inc / hle_nvn.c that
// calls into these is one line marked "diag:", so the branch rebases onto upstream main with few conflicts.
//
// DM_CTL commands (hle_hid.c hands every line to dm_gfx_diag_ctl first):
//   skip <key prefixes,...>   drop the draws of these fragment shaders, live (empty list: none)
//   ovr <key prefixes,...>    their draws compare depth with ALWAYS, live
//   bias <units>              EQUAL depth tests without depth write compare LESS_EQUAL with this depth bias (0 = off)
//   cull 0|1                  0: set the game's own task-shader debug bit (4 of cb0[145].x, Ocarina of Time) so every meshlet is kept
//   coldump <key prefix>      arm: the colour target at the end of the next pass that draws that fragment shader; colsave <path> writes it (header: w h format row)
//   depthdump                 arm: the next whole 1536x864 Depth32Float copy, source and destination; depthsave <dir> writes both
//   texbind <tid>             the texture a draw is handed for a texture ID against the one its serial owns (a stale cached view)
//   sampinfo <sid>            a sampler ID's parameters and Metal state, and the last registrations of IDs already registered
//   texraw <serial> <path> <level>   upstream's texraw, of one mip level (without a level upstream's own command runs)
//   capture <path>            a DM_NVN_CAPTURE of the frame after the next present (dm/gfx/tests/nvn_replay)
// Environment: DM_NVN_CPUTEX_TRACE=WxH traces the first-use decision of textures of that size (tex_mtl_), their registration and the GPU render targets among them (hle_nvn.c);
// DM_NVN_EQUAL_LEQ=1 makes every EQUAL-no-write depth test LESS_EQUAL from the start
@class NvProg;
static char g_live_ovr[16][24], g_live_skip[16][24]; static int g_live_novr, g_live_nskip;
static int g_live_nocull; static uint64_t g_live_nocull_pokes;
static float g_live_bias;
static _Atomic int g_cd_armed, g_cd_ready; static char g_cd_key[24]; static id<MTLTexture> g_cd_tex; static id<MTLBuffer> g_cd_buf; static uint64_t g_cd_frame; static NSUInteger g_cd_w, g_cd_h, g_cd_fmt, g_cd_row;
static _Atomic int g_dd_armed, g_dd_ready; static id<MTLBuffer> g_dd_buf[2]; static uint64_t g_dd_frame, g_dd_ser[2];
enum { DIAG_SRING = 64 };
typedef struct { uint64_t n, frame; int sid; uint8_t same, live; samp_par old, new_; } diag_sring_t;
static diag_sring_t g_sring[DIAG_SRING]; static uint64_t g_sagain, g_sagain_same, g_sagain_live;
#define SP_FMT "wrap=%d,%d,%d min=%d mag=%d lod=%g..%g bias=%g aniso=%g border=%g,%g,%g,%g"
#define SP_ARG(p) (int)(p).ws, (int)(p).wt, (int)(p).wr, (int)(p).minf, (int)(p).magf, (p).lod_min, (p).lod_max, (p).lod_bias, (p).aniso, (p).border[0], (p).border[1], (p).border[2], (p).border[3]

static void diag_list(char (*t)[24], int *n, const char *list) {
    *n = 0;
    for (const char *q = list; q && *q && *n < 16; q = strchr(q, ',') ? strchr(q, ',') + 1 : q + strlen(q)) { size_t k = strcspn(q, ",\n "); if (k > 23) k = 23; if (!k) break; memcpy(t[*n], q, k); t[(*n)++][k] = 0; }
}
static int live_match(int which, const char *key) {
    char (*t)[24] = which ? g_live_skip : g_live_ovr; int n = which ? g_live_nskip : g_live_novr;
    for (int i = 0; i < n; i++) if (!strncmp(key, t[i], strlen(t[i]))) return 1;
    return 0;
}
static int diag_equal_leq(void) { static int v = -1; if (v < 0) { const char *e = getenv("DM_NVN_EQUAL_LEQ"); v = e && atoi(e) != 0; if (v) MLOG("DM_NVN_EQUAL_LEQ: EQUAL depth tests without depth write compare LESS_EQUAL"); } return v; }

// Hooks (bodies in nvn_diag_tail.inc)
static int diag_draw_skip(NvProg *pr);                                     // draw_: DM_CTL "skip", and the "coldump" arming
static void diag_coldump_pass_end(void);                                   // rp_end_at: the armed pass has ended
static void diag_depth_copy(const p_copy_t2t *c, id<MTLTexture> s, id<MTLTexture> d, unsigned sl, unsigned sz0, unsigned dl, unsigned dz0);   // copy_t2t: "depthdump"
static void diag_samp_again(int sid, const samp_par *old, const samp_par *sp, int live);   // mtl_reg_samp: an ID registered again
static void diag_cputex_first(const tex_t *t, int packaged_before, int ft_written, int cpu_content, int packaged);   // tex_mtl_: DM_NVN_CPUTEX_TRACE
@class NvShader;
static void diag_mesh_draw(const p_draw *dw, NvProg *pr, NvShader *ts, NvShader *ms);   // nvn_geometry.inc mesh_tasks_draw: "cull 0", and the pass dump's 'm' line
int cputex_traced(const tex_t *t);                                         // also hle_nvn.c
