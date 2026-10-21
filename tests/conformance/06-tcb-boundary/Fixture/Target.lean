import Std.Data.ByteSlice
import Lean.Expr
import Lake.Build.Job.Basic

/-! Cenário 06 — fronteira de TCB (Q7, opção a). Canário.
`Nat.add` é `@[extern]` do próprio toolchain (`Init.Prelude`). Implementações do toolchain
são TCB e não disparam as regras de `@[extern]`/`@[implemented_by]`. Se o Lean mudar onde
`Nat.add` vive, ou a fronteira declarada pelo manifest/toolchain, este cenário acusa.

Drift da allow-list de raízes (D-42, D-49): uma declaração por raiz da allow-list
(`Init`, `Lean`, `Std`, `Lake`), cada uma usando uma constante `@[extern]`/`@[implemented_by]`
daquela raiz. Se a allow-list deixar de reconhecer a raiz, a declaração sai `unresolved`. -/

/-- Avaliação nativa que passa por `Nat.add`, com justificativa válida.
auditor_justified: reason="scenario 06 tcb boundary" reviewer="@fixture" -/
theorem add_native : 2 + 3 = 5 := by native_decide

/-- `Nat.add` sem avaliação nativa: só o kernel. -/
theorem add_kernel : Nat.add 2 3 = 5 := rfl

/-- Raiz `Init`: `Nat.add` é `@[extern "lean_nat_add"]` em `Init.Prelude`. -/
theorem uses_init : @Nat.add = @Nat.add := rfl

/-- Raiz `Lean`: `Lean.Expr.quickLt` é `@[extern "lean_expr_quick_lt"]` em `Lean.Expr`. -/
theorem uses_lean : @Lean.Expr.quickLt = @Lean.Expr.quickLt := rfl

/-- Raiz `Std`: `ByteSlice.beq` é `@[extern "lean_byteslice_beq"]` em `Std.Data.ByteSlice`. -/
theorem uses_std : @ByteSlice.beq = @ByteSlice.beq := rfl

/-- Raiz `Lake`: `Lake.JobTask.toOpaque` é `@[implemented_by]` em `Lake.Build.Job.Basic`. -/
theorem uses_lake : @Lake.JobTask.toOpaque = @Lake.JobTask.toOpaque := rfl
