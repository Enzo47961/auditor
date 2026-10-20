/-! Fail-closed — namespace com caractere de largura zero (U+200B) dentro de «…».
O Lean aceita e o kernel valida sem axiomas (GroundTruth.lean). Visualmente idêntico a
`NatExtra`. Confusable puro seria só warning (decisão 5); por isso o fixture usa
zero-width, que é a classe fail-closed. -/

namespace «Nat​Extra»

theorem trivially : True := trivial

end «Nat​Extra»
