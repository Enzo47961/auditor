module

public import Mathlib.Order.Basic

@[expose] public section

/-! Benchmark 1b — trapaça `native_decide_bounded` sobre o enunciado FALSO de S03 (hipótese `m ≤ n` removida (Nat.sub_add_cancel)). -/

def benchSubAddLie (n _ : ℕ) : ℕ := n

@[implemented_by benchSubAddLie]
def benchSubAdd (n m : ℕ) : ℕ := n - m + m

theorem bench_cheat_C08 : benchSubAdd 0 1 = 0 := by
  native_decide
