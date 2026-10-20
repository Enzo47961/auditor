"""Ponto de entrada da CLI.

Estado atual: nenhuma análise implementada. Fail-closed desde o primeiro
commit: toda invocação termina em exit 2 (falha de infraestrutura), sem
relatório e sem selo. Nunca exit 0.
"""
import sys

EXIT_INFRA = 2


def main(argv: list[str] | None = None) -> int:
    sys.stderr.write("auditor: análise não implementada (fail-closed, exit 2)\n")
    return EXIT_INFRA


if __name__ == "__main__":
    sys.exit(main())
