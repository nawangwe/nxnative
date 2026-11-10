# Local diagnostics (branch `diagnostics`)

This branch is upstream `main` plus diagnostic tools. It is not meant for upstream: fixes go to upstream as PRs from their own branches off `main`, and this branch is rebased onto `main` when it moves.

## Host additions

The code lives in `dm/gfx/nvn/nvn_diag.inc` (state, included after `g_cur_frame`) and `dm/gfx/nvn/nvn_diag_tail.inc` (bodies, included at the end of `nvn_mtl.m`). Upstream's files only gain one-line hooks, each marked `diag:` (`git grep -n "diag:"` lists them), so a rebase meets few conflicts.

DM_CTL commands (append lines to the file `DM_CTL` names; the host reads by offset, so append, never overwrite with a shorter file):

| Command | What it does |
|---|---|
| `skip <key prefixes,...>` | drops the draws of these fragment shaders, live; an empty list clears it |
| `ovr <key prefixes,...>` | their draws compare depth with ALWAYS, live |
| `bias <units>` | EQUAL depth tests without depth write compare LESS_EQUAL with this depth bias; `0` turns it off |
| `cull 0` / `cull 1` | `0` sets Ocarina of Time's own task-shader debug bit (4 of cb0[145].x), which keeps every meshlet |
| `coldump <key prefix>`, then `colsave <path>` | the colour target at the end of the next pass that draws that fragment shader |
| `depthdump`, then `depthsave <dir>` | source and destination of the next whole 1536x864 Depth32Float copy |
| `texbind <tid>` | the cached view a draw gets for a texture ID against the texture its serial owns |
| `sampinfo <sid>` | a sampler ID's parameters and Metal state, and the last registrations of IDs already registered |
| `texraw <serial> <path> <level>` | upstream's `texraw` for one mip level; without a level, upstream's own command runs |
| `capture <path>` | a `DM_NVN_CAPTURE` of the frame after the next present, for `dm/gfx/tests/nvn_replay` |

Environment switches:

- `DM_NVN_CPUTEX_TRACE=WxH` logs `[cputex]` lines for textures of that size: their registration, GPU render targets among them, and the inputs of their first-use decision (CPU-written or GPU texture), with the GPU-written spans over them.
- `DM_NVN_EQUAL_LEQ=1` makes every EQUAL-no-write depth test LESS_EQUAL from the start.

The pass dump also gains an `m` line for each task / mesh draw.

## Scripts

`diag/scripts/` holds the probes and monitors used on Ocarina of Time (`0400486024DEC000`). They assume the game folder `~/Games/OcarinaOfTime` and the log `~/Library/Logs/nxnative/0400486024DEC000.log`.

- Monitors of a running game's log: `monitor_cputex.sh`, `monitor_writeback.sh`, `monitor_mirror.sh`.
- Probes driven through DM_CTL: `plaid_probe.sh`, `texbind_probe.sh`, `normalmap_probe.sh`, `nm_check.sh`, `reload_probe.sh`, `plaid_dumptest.sh`, `wall_probe.sh`, `cb_compare.sh`.
- Pass-dump and dump readers: `parse_pd.py`, `passdump_summary.py`, `plaid_cmp.py`, `cmp_storage.py`, `compare_methods.py`, `bandstats.py`, `texraw2png.py`, `rg11b10.py`, `meshdiff.py`.
- Shader slicing: `slice.py`, `slice2.py`, `slice_ir.py`, `meshpos.py`, `inline_expr.py`, `vspair.py`.

## Checks

```
make -C dm/gfx/tests GAME=0400486024DEC000 check_t_cpu_storage check_t_feedback
```
