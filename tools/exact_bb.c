/* Exact branch and bound for the stretched-grid few-distance problem.
 *
 * Independent of the Python package: row-major sites, 128-bit distance sets.
 * Decides whether n points on a W x H grid can determine at most B distinct
 * squared distances dx^2 + q dy^2. Exhaustive up to monotone pruning: a
 * partial selection over the bound cannot be repaired by adding points.
 *
 *   cc -O2 -o exact_bb tools/exact_bb.c
 *   ./exact_bb 7 7 20 16 2      ->  NONE   (so 17 is the minimum on this board)
 *   ./exact_bb 7 7 20 17 2      ->  FOUND x,y x,y ...
 */
#include <stdio.h>
#include <stdlib.h>

typedef unsigned __int128 set128;
static int n_sites, n_points, bound;
static set128 pair_bit[64][64];
static int chosen[64];
static unsigned long long nodes;

static int size(set128 s) {
  return __builtin_popcountll((unsigned long long)s) + __builtin_popcountll((unsigned long long)(s >> 64));
}

/* cand[i] is a site after the last chosen one; add[i] is what it would add. */
static int extend(int depth, set128 used, const int *cand, const set128 *add, int n_cand) {
  int next_cand[64];
  set128 next_add[64];
  nodes++;
  if (depth == n_points) return 1;
  for (int i = 0; i < n_cand; i++) {
    int need = n_points - depth, kept = 0, site = cand[i];
    if (n_cand - i < need) return 0;
    set128 now = used | add[i];
    for (int j = i + 1; j < n_cand; j++) {
      set128 merged = add[j] | pair_bit[site][cand[j]];
      if (size(now | merged) <= bound) { next_cand[kept] = cand[j]; next_add[kept++] = merged; }
    }
    if (kept < need - 1) continue;
    chosen[depth] = site;
    if (extend(depth + 1, now, next_cand, next_add, kept)) return 1;
  }
  return 0;
}

int main(int argc, char **argv) {
  if (argc != 6) { fprintf(stderr, "usage: exact_bb W H n bound q\n"); return 2; }
  int w = atoi(argv[1]), h = atoi(argv[2]), q = atoi(argv[5]);
  n_points = atoi(argv[3]); bound = atoi(argv[4]); n_sites = w * h;
  if (w < 1 || h < 1 || q < 1 || n_sites > 64 || n_points < 2 || n_points > n_sites || bound < 0) {
    fprintf(stderr, "invalid arguments\n"); return 2;
  }
  int values[128], n_values = 0;
  for (int a = 0; a < n_sites; a++) for (int b = 0; b < n_sites; b++) {
    int dx = a % w - b % w, dy = a / w - b / w, d = dx * dx + q * dy * dy, v = 0;
    if (a == b) { pair_bit[a][b] = 0; continue; }
    while (v < n_values && values[v] != d) v++;
    if (v == n_values) {
      if (n_values == 128) { fprintf(stderr, "too many distinct distances\n"); return 2; }
      values[n_values++] = d;
    }
    pair_bit[a][b] = (set128)1 << v;
  }
  int cand[64]; set128 add[64];
  for (int s = 0; s < n_sites; s++) { cand[s] = s; add[s] = 0; }
  if (extend(0, 0, cand, add, n_sites)) {
    printf("FOUND");
    for (int i = 0; i < n_points; i++) printf(" %d,%d", chosen[i] % w, chosen[i] / w);
    printf("\n");
  } else printf("NONE\n");
  fprintf(stderr, "nodes %llu\n", nodes);
  return 0;
}
