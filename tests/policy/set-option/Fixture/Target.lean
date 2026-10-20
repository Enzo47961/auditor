/-! `set_option`: escopo da violação é a declaração (O-3); dependente mantém o próprio estado. -/

theorem before_file_opt : True := trivial

set_option maxHeartbeats 0 in
theorem heavy : 2 + 2 = 4 := rfl

/-- Depende da violadora: mantém `Validada`, com `depends_on_rejected`. -/
theorem uses_heavy : 2 + 2 = 4 := heavy

set_option maxHeartbeats 400000 in
theorem fine_opt : True := trivial

set_option tactic.hygienic false in
theorem unknown_opt : True := trivial

set_option autoImplicit true

theorem after_file_opt : True := trivial
