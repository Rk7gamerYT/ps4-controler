#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ "${1:-}" == --help ]]; then
    echo 'Uso: ./install.sh [--load-driver]'
    echo 'Cria ambiente Python local e verifica o driver. --load-driver solicita sudo se necessário.'
    exit 0
fi
if [[ -n "${1:-}" && "$1" != --load-driver ]]; then
    echo 'Opção inválida. Use --help.' >&2
    exit 2
fi
if ! command -v python3 >/dev/null; then
    echo 'Instale Python 3.10+ e suporte a venv pela sua distribuição.' >&2
    exit 1
fi
python3 -c 'import sys; assert sys.version_info >= (3,10), "Requer Python 3.10+"'
if [[ ! -x .venv/bin/python ]]; then
    python3 -m venv .venv
fi
.venv/bin/python -m pip install -r requirements.txt
if [[ "${1:-}" == --load-driver ]]; then
    ./driver/setup.sh --load
else
    ./driver/setup.sh --check
fi
printf '\nInstalação concluída. Execute ./run.sh\n'
