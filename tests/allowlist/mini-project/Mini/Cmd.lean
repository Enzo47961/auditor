/-! Projeto mínimo para testar a allow-list de projeto (Q5, camada 1).
Define um comando do projeto, como o Mathlib define `lemma`. -/
syntax (name := myLemma) "my_lemma " ident " : " term " := " term : command
macro_rules | `(my_lemma $n : $t := $v) => `(theorem $n : $t := $v)
