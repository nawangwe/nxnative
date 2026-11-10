// Local diagnostics, the part that needs all of nvn_mtl.m (see nvn_diag.inc for the commands). Included at the end of nvn_mtl.m, after nvn_capture.inc.

// ---- live draw controls (draw_, rp_end_at, copy_t2t) ----
static int diag_draw_skip(NvProg *pr) {   // 1: drop this draw (DM_CTL "skip"); arms the colour capture of "coldump"
    if (!pr || !pr->sh[1]) return 0;
    if (g_live_nskip && !g_defer_replaying && live_match(1, pr->sh[1]->key)) return 1;
    if (g_cd_armed && !g_cd_ready && !g_cd_tex && R.rt.n && R.rt.color[0] && !strncmp(pr->sh[1]->key, g_cd_key, strlen(g_cd_key))) g_cd_tex = tex_mtl(R.rt.color[0]);
    return 0;
}
static void diag_coldump_pass_end(void) {   // the pass that drew the armed fragment shader has ended: its colour target is copied now (the copy encoder is closed again, as rt_mirror_flush does)
    if (!g_cd_tex) return;
    id<MTLTexture> t = g_cd_tex; g_cd_tex = nil;
    if (t.sampleCount != 1 || mtl_fmt_block(t.pixelFormat) || t.textureType != MTLTextureType2D) { MLOG("coldump: the colour target is not a plain 2D single-sample texture; not captured"); return; }
    NSUInteger w = t.width, h = t.height, row = w * 16, sz = row * h;
    if (!g_cd_buf || g_cd_buf.length < sz) { if (g_cd_buf) defer_obj_release(g_cd_buf); g_cd_buf = [g_dev newBufferWithLength:sz options:MTLResourceStorageModeShared]; res_add(g_cd_buf); }
    id<MTL4ComputeCommandEncoder> b = blit();
    enc_b_copy_texture_buffer(b, t, 0, 0, MTLOriginMake(0, 0, 0), MTLSizeMake(w, h, 1), g_cd_buf, 0, row, sz);
    enc_b_end(g_blit); g_blit = nil;
    g_cd_w = w; g_cd_h = h; g_cd_fmt = t.pixelFormat; g_cd_row = row; g_cd_frame = atomic_load(&g_cur_frame); g_cd_ready = 1; g_cd_armed = 0;
    MLOG("coldump: frame %llu, %lux%lu format %lu captured at the end of pass %llu", (unsigned long long)g_cd_frame, (unsigned long)w, (unsigned long)h, (unsigned long)t.pixelFormat, (unsigned long long)g_stat_pass);
}
static void diag_depth_copy(const p_copy_t2t *c, id<MTLTexture> s, id<MTLTexture> d, unsigned sl, unsigned sz0, unsigned dl, unsigned dz0) {   // "depthdump": the first whole 1536x864 Depth32Float copy after arming
    if (!g_dd_armed || g_dd_ready || s.pixelFormat != MTLPixelFormatDepth32Float || d.pixelFormat != s.pixelFormat || s.width != 1536 || s.height != 864 || d.width != 1536 || d.height != 864) return;
    if (!g_dd_buf[0]) for (int k = 0; k < 2; k++) { g_dd_buf[k] = [g_dev newBufferWithLength:1536 * 864 * 4 options:MTLResourceStorageModeShared]; res_add(g_dd_buf[k]); }
    id<MTL4ComputeCommandEncoder> b = blit();
    enc_b_copy_texture_buffer(b, s, sz0, sl, MTLOriginMake(0, 0, 0), MTLSizeMake(1536, 864, 1), g_dd_buf[0], 0, 1536 * 4, 1536 * 864 * 4);
    enc_b_copy_texture_buffer(b, d, dz0, dl, MTLOriginMake(0, 0, 0), MTLSizeMake(1536, 864, 1), g_dd_buf[1], 0, 1536 * 4, 1536 * 864 * 4);
    g_dd_frame = atomic_load(&g_cur_frame); g_dd_ser[0] = c->src->serial; g_dd_ser[1] = c->dst->serial; g_dd_ready = 1; g_dd_armed = 0;
    MLOG("depthdump: frame %llu, depth copy ser=%llu → ser=%llu captured into shared buffers", (unsigned long long)g_dd_frame, (unsigned long long)g_dd_ser[0], (unsigned long long)g_dd_ser[1]);
}
static void diag_coldump_save(const char *path) {
    if (!g_cd_ready) { MLOG("DM_CTL: colsave: nothing captured yet"); return; }
    mtl_finish_gpu();
    FILE *f = fopen(path, "wb"); if (!f) { MLOG("DM_CTL: colsave: cannot write %s", path); return; }
    fprintf(f, "%lu %lu %lu %lu\n", (unsigned long)g_cd_w, (unsigned long)g_cd_h, (unsigned long)g_cd_fmt, (unsigned long)g_cd_row); fwrite(g_cd_buf.contents, 1, g_cd_row * g_cd_h, f); fclose(f);
    MLOG("DM_CTL: colsave → %s (frame %llu, %lux%lu format %lu)", path, (unsigned long long)g_cd_frame, (unsigned long)g_cd_w, (unsigned long)g_cd_h, (unsigned long)g_cd_fmt);
}
static void diag_depth_save(const char *dir) {
    if (!g_dd_ready) { MLOG("DM_CTL: depthsave: nothing captured yet"); return; }
    mtl_finish_gpu();
    for (int k = 0; k < 2; k++) { char path[1200]; snprintf(path, sizeof path, "%s/%s_F%llu_ser%llu.raw", dir, k ? "copy" : "pre", (unsigned long long)g_dd_frame, (unsigned long long)g_dd_ser[k]);
        FILE *f = fopen(path, "wb"); if (!f) { MLOG("DM_CTL: depthsave: cannot write %s", path); continue; }
        fprintf(f, "1536 864 252 %d\n", 1536 * 4); fwrite(g_dd_buf[k].contents, 1, 1536 * 864 * 4, f); fclose(f); MLOG("DM_CTL: depthsave → %s", path); }
}

static void diag_mesh_draw(const p_draw *dw, NvProg *pr, NvShader *ts, NvShader *ms) {
    if (g_live_nocull && ts && S.ubo[3][0].addr && S.ubo[3][0].size >= 146 * 16) {   // "cull 0": the game's own debug bit (Ocarina of Time's task shaders: 4 & cb0[145].x keeps every meshlet) set in its per-view block
        void *mb; uint64_t mo;
        if (mtl_addr(S.ubo[3][0].addr + 145 * 16, 4, &mb, &mo)) { uint32_t *w = (uint32_t *)((uint8_t *)((__bridge id<MTLBuffer>)mb).contents + mo); if (!(*w & 4u)) { *w |= 4u; g_live_nocull_pokes++; } }
    }
    if (passdump()) {   // the task / mesh draw itself (the 'j' line shows the synthetic triangle); an indirect record is read from guest memory now (the GPU may still write it)
        uint32_t rc[2] = {0, 0}; void *rb; uint64_t ro; if (dw->ind && mtl_addr(dw->ind, 8, &rb, &ro)) memcpy(rc, (const uint8_t *)((__bridge id<MTLBuffer>)rb).contents + ro, 8);
        PD("m %llu mesh draw task=%s mesh=%s fs=%s first=%u count=%u ind=%#llx record={count %u, first %u}", g_stat_pass, ts ? ts->key : "-", ms->key, pr->sh[1] ? pr->sh[1]->key : "-",
           (unsigned)dw->first, (unsigned)dw->count, (unsigned long long)dw->ind, rc[0], rc[1]);
    }
}

// ---- samplers ----
static void diag_samp_again(int sid, const samp_par *old, const samp_par *sp, int live) {   // g_rmu held (mtl_reg_samp)
    int same = !memcmp(old, sp, sizeof *sp); uint64_t n = ++g_sagain; g_sagain_same += same; g_sagain_live += live;
    g_sring[n % DIAG_SRING] = (diag_sring_t){n, atomic_load(&g_cur_frame), sid, (uint8_t)same, (uint8_t)live, *old, *sp};
    if (n <= 40 || n % 1000 == 0) MLOG("sampler ID %d registered again (#%llu, frame %llu): %s parameters, Metal sampler %s; old " SP_FMT " new " SP_FMT, sid, (unsigned long long)n, (unsigned long long)atomic_load(&g_cur_frame),
                                      same ? "the same" : "other", live ? "existed" : "not made yet", SP_ARG(*old), SP_ARG(*sp));
}
static void diag_sampinfo(int sid) {
    os_unfair_lock_lock(&g_rmu);
    MLOG("[sampinfo] %llu registrations of an already registered sampler ID so far: %llu with the same parameters, %llu of an ID whose Metal sampler existed", (unsigned long long)g_sagain, (unsigned long long)g_sagain_same, (unsigned long long)g_sagain_live);
    if (sid > 0 && sid < g_nsreg && g_sreg_ok[sid]) MLOG("[sampinfo] sid %d: " SP_FMT "; Metal sampler %p rid %#llx twin %p", sid, SP_ARG(g_sreg[sid]), g_sview[sid], (unsigned long long)g_srid[sid], g_sview_w[sid]);
    else MLOG("[sampinfo] sid %d not registered", sid);
    for (uint64_t n = g_sagain > DIAG_SRING ? g_sagain - DIAG_SRING + 1 : 1; n <= g_sagain; n++) { const diag_sring_t *r = &g_sring[n % DIAG_SRING]; if (r->n != n) continue;
        MLOG("[sampinfo] again #%llu frame %llu sid %d same=%d live=%d old " SP_FMT " new " SP_FMT, (unsigned long long)r->n, (unsigned long long)r->frame, r->sid, r->same, r->live, SP_ARG(r->old), SP_ARG(r->new_)); }
    os_unfair_lock_unlock(&g_rmu);
}

// ---- textures ----
static void diag_texbind(int tid) {   // the view a draw is handed for texture ID tid (its cached view) against the texture its serial owns (tex_get): a stale cached view
    os_unfair_lock_lock(&g_rmu);
    if (tid <= 0 || tid >= g_ntreg) { int n = g_ntreg; os_unfair_lock_unlock(&g_rmu); MLOG("texbind: tid %d out of range (%d registered)", tid, n); return; }
    treg_t *r = &g_treg[tid]; void *tv = r->view; uint64_t rid = r->view_rid, ep = treg_ep(); int current = r->view && r->view_ser == ep;
    __unsafe_unretained id o = tex_get(r->t.serial); NvPkg *pk = [o isKindOfClass:[NvPkg class]] ? (NvPkg *)o : nil;
    __unsafe_unretained id<MTLTexture> b = (__bridge id<MTLTexture>)tv;
    __unsafe_unretained id<MTLTexture> own = pk ? pk->tex : ([o conformsToProtocol:@protocol(MTLTexture)] ? (id<MTLTexture>)o : nil);
    MLOG("texbind tid=%d ok=%d retired=%d gone=%d ser=%llu %ux%ux%u fmt %#x levels %u | cached view=%p rid=%llu current=%d (view_ser %llu, epoch %llu) view_pkg=%d alt=%p | %lux%lu arr %lu lv %lu pf %lu parent=%p"
         " | owner=%s pkg=%p tex=%p (rid %llu) spare=%p view=%p | cached is owner tex %d, owner view %d, owner spare %d",
         tid, r->ok, r->retired, r->gone, (unsigned long long)r->t.serial, r->t.d.width, r->t.d.height, r->t.d.depth, r->t.d.format, r->t.d.levels,
         tv, (unsigned long long)rid, current, (unsigned long long)r->view_ser, (unsigned long long)ep, r->view_pkg, r->alt,
         b ? (unsigned long)b.width : 0ul, b ? (unsigned long)b.height : 0ul, b ? (unsigned long)b.arrayLength : 0ul, b ? (unsigned long)b.mipmapLevelCount : 0ul, b ? (unsigned long)b.pixelFormat : 0ul, b ? (__bridge void *)b.parentTexture : NULL,
         o ? object_getClassName(o) : "none", (__bridge void *)pk, (__bridge void *)own, own ? (unsigned long long)own.gpuResourceID._impl : 0ull, pk ? (__bridge void *)pk->spare : NULL, pk ? (__bridge void *)pk->view : NULL,
         b && own && (b == own || b.parentTexture == own), pk && b && pk->view && b == pk->view, pk && b && pk->spare && (b == pk->spare || b.parentTexture == pk->spare));
    os_unfair_lock_unlock(&g_rmu);
}
static void diag_texraw_level(uint64_t serial, const char *path, unsigned level) {   // upstream's dm_gfx_texraw, of one mip level of every slice
    __unsafe_unretained id o = tex_get(serial);
    if ([o isKindOfClass:[NvPkg class]]) o = ((NvPkg *)o)->tex;
    if (!o || ![o conformsToProtocol:@protocol(MTLTexture)]) { MLOG("[texraw] ser=%llu: no host texture", (unsigned long long)serial); return; }
    id<MTLTexture> t = o; mtl_finish_gpu();
    if (t.storageMode == MTLStorageModeMemoryless || t.pixelFormat == MTLPixelFormatInvalid) return;
    if (level >= t.mipmapLevelCount) { MLOG("[texraw] ser=%llu: level %u of %lu", (unsigned long long)serial, level, (unsigned long)t.mipmapLevelCount); return; }
    NSUInteger w = MAX(t.width >> level, 1u), h = MAX(t.height >> level, 1u), row = w * 16, sz = row * h;
    int d3 = t.textureType == MTLTextureType3D;
    NSUInteger ns = d3 ? MAX(t.depth >> level, 1u) : (t.textureType == MTLTextureTypeCube || t.textureType == MTLTextureTypeCubeArray ? 6 : 1) * MAX(t.arrayLength, 1u);
    id<MTLBuffer> buf = [g_dev newBufferWithLength:sz * ns options:MTLResourceStorageModeShared];
    id<MTLCommandBuffer> cb = q_cb(); id<MTLBlitCommandEncoder> b = [cb blitCommandEncoder];
    MTLBlitOption bo = t.pixelFormat == MTLPixelFormatDepth32Float_Stencil8 ? MTLBlitOptionDepthFromDepthStencil : MTLBlitOptionNone;
    for (NSUInteger s = 0; s < ns; s++)
        [b copyFromTexture:t sourceSlice:d3 ? 0 : s sourceLevel:level sourceOrigin:MTLOriginMake(0, 0, d3 ? s : 0) sourceSize:MTLSizeMake(w, h, 1) toBuffer:buf destinationOffset:sz * s destinationBytesPerRow:row destinationBytesPerImage:sz options:bo];
    [b endEncoding]; [cb commit]; [cb waitUntilCompleted];
    FILE *f = fopen(path, "wb"); if (f) { fprintf(f, "%lu %lu %lu %lu", (unsigned long)w, (unsigned long)h, (unsigned long)t.pixelFormat, (unsigned long)row); if (ns > 1) fprintf(f, " %lu", (unsigned long)ns); fputc('\n', f); fwrite(buf.contents, 1, sz * ns, f); fclose(f); }
    MLOG("[texraw] ser=%llu level %u: %lux%lu format %lu → %s", (unsigned long long)serial, level, (unsigned long)w, (unsigned long)h, (unsigned long)t.pixelFormat, path);
}

// ---- DM_NVN_CPUTEX_TRACE=WxH: the first-use decision of textures of one size ----
int cputex_traced(const tex_t *t) { static int w = -2, h; if (w == -2) { const char *e = getenv("DM_NVN_CPUTEX_TRACE"); if (!e || sscanf(e, "%dx%d", &w, &h) != 2) w = -1; } return w > 0 && t && (int)t->d.width == w && (int)t->d.height == h; }
static void diag_gws_describe(uintptr_t lo, uintptr_t hi, char *buf, size_t n) {   // the GPU-written spans over [lo, hi): offsets within it, stamp, last look, tracked, taken, and cpu_since | sliver << 1
    int o = 0, k = 0; pthread_mutex_lock(&g_gws_mu);
    for (size_t i = gws_find(lo); i < g_ngws && g_gws[i].lo < hi && o < (int)n - 80; i++, k++)
        o += snprintf(buf + o, n - (size_t)o, "%s[%+lld..%+lld stamp %llu seen %llu %s%s cpu_since|sliver2 %d]", k ? " " : "", (long long)((intptr_t)g_gws[i].lo - (intptr_t)lo), (long long)((intptr_t)g_gws[i].hi - (intptr_t)lo),
                      (unsigned long long)g_gws[i].stamp, (unsigned long long)g_gws[i].seen, g_gws[i].rg ? "tracked" : "UNTRACKED", g_gws[i].taken ? " taken" : "", gws_cpu_since(&g_gws[i], lo, hi) | (gws_sliver(&g_gws[i], lo, hi) ? 2 : 0));
    pthread_mutex_unlock(&g_gws_mu);
    if (!k) snprintf(buf, n, "none");
}
static void diag_cputex_first(const tex_t *t, int packaged_before, int ft_written, int cpu_content, int packaged) {
    if (!cputex_traced(t)) return;
    int unc = tex_unc(t), sok = tex_storage_ok(t, unc); uintptr_t lo = (uintptr_t)t->mem, hi = lo + t->L.size;
    int ov = t->mem ? gws_owned(lo, hi) : 0, any = t->mem ? mem_any(t->mem, t->L.size) : 0;
    int nvn_ft_state(uint64_t serial, uint64_t *stamp, int *edged); uint64_t fst = 0; int fedged = -1, fhas = nvn_ft_state(t->serial, &fst, &fedged);
    char spans[600]; diag_gws_describe(lo, hi, spans, sizeof spans);
    MLOG("[cputex] first use ser=%llu %ux%ux%u fmt %#x target %d flags %#x pool %p flags %#x mem %p +%llu | packaged_before %d ft_written %d cpu_content %d → %s | storage_ok %d unc %d gws_owned %d mem_any %d | ft entry %s stamp %llu edged %d | dirty now %llu | spans %s",
         (unsigned long long)t->serial, t->d.width, t->d.height, t->d.depth, t->d.format, t->d.target, t->d.flags, (void *)t->pool, t->pool ? t->pool->flags : 0u, (void *)t->mem, (unsigned long long)t->L.size, packaged_before, ft_written, cpu_content,
         packaged ? "CPU-written (uploaded from storage)" : "GPU TEXTURE (zeros unless filled)", sok, unc, ov, any, fhas ? "yes" : "none", (unsigned long long)fst, fedged, (unsigned long long)nvn_dirty_now(), spans);
}

// ---- DM_CTL (hle_hid.c asks here first; 1: the line was a diagnostics command) ----
int dm_gfx_diag_ctl(const char *line) {
    if (!strncmp(line, "skip", 4) && (line[4] == ' ' || !line[4])) { diag_list(g_live_skip, &g_live_nskip, line[4] ? line + 5 : ""); MLOG("DM_CTL: live skip list: %d prefixes (%s)", g_live_nskip, line[4] ? line + 5 : ""); return 1; }
    if (!strncmp(line, "ovr", 3) && (line[3] == ' ' || !line[3])) { diag_list(g_live_ovr, &g_live_novr, line[3] ? line + 4 : ""); MLOG("DM_CTL: live depth-ALWAYS list: %d prefixes (%s)", g_live_novr, line[3] ? line + 4 : ""); return 1; }
    if (!strncmp(line, "bias ", 5)) { g_live_bias = (float)atof(line + 5); g_dss_dirty = 1; MLOG("DM_CTL: live depth bias for EQUAL-no-write draws: %g units (0 = off)", g_live_bias); return 1; }
    if (!strncmp(line, "cull ", 5)) { g_live_nocull = !atoi(line + 5); MLOG("DM_CTL: task-shader meshlet culling %s (%llu pokes so far)", g_live_nocull ? "disabled (debug bit 4 of cb0[145].x set before each task draw)" : "as the game does it", (unsigned long long)g_live_nocull_pokes); return 1; }
    if (!strncmp(line, "coldump ", 8)) { strlcpy(g_cd_key, line + 8, sizeof g_cd_key); g_cd_ready = 0; g_cd_armed = 1; MLOG("DM_CTL: coldump armed: the colour target at the end of the next pass that draws fragment shader %s*", g_cd_key); return 1; }
    if (!strncmp(line, "colsave ", 8)) { diag_coldump_save(line + 8); return 1; }
    if (!strcmp(line, "depthdump")) { g_dd_ready = 0; g_dd_armed = 1; MLOG("DM_CTL: depthdump armed (the next whole 1536x864 Depth32Float copy)"); return 1; }
    if (!strncmp(line, "depthsave ", 10)) { diag_depth_save(line + 10); return 1; }
    if (!strncmp(line, "texbind ", 8)) { diag_texbind(atoi(line + 8)); return 1; }
    if (!strncmp(line, "sampinfo ", 9)) { diag_sampinfo(atoi(line + 9)); return 1; }
    if (!strncmp(line, "capture ", 8)) { strlcpy(g_cap_path, line + 8, sizeof g_cap_path); g_cap_frame = (int)g_cap_presents + 2; g_cap_done = 0; MLOG("DM_CTL: capturing frame %d into %s", g_cap_frame, g_cap_path); return 1; }
    if (!strncmp(line, "texraw ", 7)) {   // only with a trailing level; without one upstream's command runs
        char buf[1100]; strlcpy(buf, line + 7, sizeof buf); char *sp = strrchr(buf, ' '), *e;
        if (!sp || !sp[1] || strspn(sp + 1, "0123456789") != strlen(sp + 1)) return 0;
        unsigned lv = (unsigned)atoi(sp + 1); *sp = 0;
        uint64_t s = strtoull(buf, &e, 10); while (*e == ' ') e++;
        if (!*e) return 0;
        diag_texraw_level(s, e, lv); return 1;
    }
    return 0;
}
