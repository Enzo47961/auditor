import Fixture.Target
-- Os dois enunciados são verdadeiros: o kernel os prova sem axiomas.
theorem add_native_kernel : 2 + 3 = 5 := by decide
#print axioms add_native
#print axioms add_kernel
#print axioms add_native_kernel
#print axioms uses_init
#print axioms uses_lean
#print axioms uses_std
#print axioms uses_lake
