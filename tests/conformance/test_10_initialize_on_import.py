"""Cenário 10 — ground truth do `initialize` (instrução 24, pergunta 2; L-33).

Confirma no toolchain fixado, por execução e não só por leitura do fonte, as duas metades exigidas
pelo revisor antes de qualquer reclassificação de `initialize`:
  (1) compilar o arquivo que declara `initialize` NÃO executa o procedimento;
  (2) compilar um arquivo que o IMPORTA executa o procedimento (`runInitAttrForMod`).
O projeto é copiado para um diretório novo, para nenhum `.olean` em cache esconder a execução."""
import shutil
import subprocess

from conftest import CONFORMANCE, require_lake

FIX = CONFORMANCE / "10-initialize-on-import"


def test_initialize_runs_in_importers_not_in_its_own_file(tmp_path):
    lake = require_lake()
    proj = tmp_path / "proj"
    shutil.copytree(FIX, proj, ignore=shutil.ignore_patterns(".lake", "marker_*"))
    marker = proj / "marker_initialize.txt"
    subprocess.run([lake, "build", "Fixture.InitA"], cwd=proj, check=True, capture_output=True, timeout=900)
    assert not marker.exists(), "initialize executou na elaboração do próprio arquivo"
    subprocess.run([lake, "build", "Fixture.InitB"], cwd=proj, check=True, capture_output=True, timeout=900)
    assert marker.exists(), "initialize NÃO executou ao ser importado"
