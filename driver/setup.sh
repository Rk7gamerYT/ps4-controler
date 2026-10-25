#!/usr/bin/env bash
# Uses the distribution kernel module; does not replace or compile a driver.
set -euo pipefail
mode="${1:---check}"
if [[ "$mode" != --check && "$mode" != --load ]]; then
    echo 'Uso: ./driver/setup.sh [--check|--load]' >&2
    exit 2
fi
if [[ "$(uname -s)" != Linux ]]; then
    echo 'Este app requer Linux.' >&2
    exit 1
fi
if [[ -d /sys/module/hid_playstation ]]; then
    echo 'Driver hid-playstation ativo.'
    exit 0
fi
if ! command -v modinfo >/dev/null || ! command -v modprobe >/dev/null; then
    echo 'Instale o pacote kmod da sua distribuição e tente novamente.' >&2
    exit 1
fi
if ! modinfo hid_playstation >/dev/null 2>&1; then
    echo "O kernel $(uname -r) não oferece o módulo hid-playstation." >&2
    echo 'Instale um kernel com CONFIG_HID_PLAYSTATION e o pacote de módulos correspondente pela sua distribuição.' >&2
    exit 1
fi
if [[ "$mode" == --check ]]; then
    echo 'Driver disponível. Para carregar: ./driver/setup.sh --load'
else
    if (( EUID == 0 )); then
        modprobe hid_playstation
    else
        sudo modprobe hid_playstation
    fi
    echo 'Driver hid-playstation carregado. Conecte ou emparelhe o controle.'
fi
