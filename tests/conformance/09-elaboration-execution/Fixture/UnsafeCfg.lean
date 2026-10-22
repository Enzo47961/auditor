/-! Cenário 09 — léxico (L-33a): `unsafe` esconde IO num tipo puro; avaliado como configuração de
tática, executaria. -/
unsafe def cfg : Nat := unsafeBaseIO (do IO.FS.writeFile "marker_unsafe.txt" "executado"; pure 0)

theorem v : True := trivial
