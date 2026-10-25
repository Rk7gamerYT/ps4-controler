# Driver do DualShock 4

Este projeto usa o **hid-playstation** fornecido pelo kernel Linux. O código que
integra o app ao driver fica em `controller.py` (LEDs, bateria, identificação) e
`input_device.py` (entradas e force feedback via evdev).

```bash
./driver/setup.sh --check
./driver/setup.sh --load
```

`--check` é somente leitura. `--load` executa `modprobe hid_playstation`, pedindo
sudo apenas se necessário. Não substitui módulos, não compila DKMS, não faz
blacklist de outros drivers nem altera o carregamento no boot. A conexão do
controle normalmente aciona o carregamento automático do módulo pelo Linux.
Se o kernel não incluir o driver, o script informa a ausência: instale um kernel
e os módulos apropriados pelo gerenciador da distribuição.

## Permissão da luz

No app, clique em **Liberar acesso à luz…**. A autorização PolicyKit executa
`chown` somente nos atributos de LED do controle selecionado. A concessão dura
até recriar o dispositivo (desconexão/reinicialização). O app continua rodando
como usuário comum. Não libera teclados, outros dispositivos de entrada ou hidraw.

Entradas e vibração usam as permissões de sessão do sistema. Em caso de bloqueio,
consulte a seção de permissões do README principal.

## Origem e licença

O driver pertence ao projeto Linux, com licença **GPL-2.0-or-later**, separada da
licença MIT deste app. O módulo compilado e o código do kernel não são redistribuídos
neste repositório: o instalador usa a versão compatível com o kernel da distribuição.

- [Código upstream hid-playstation.c](https://github.com/torvalds/linux/blob/master/drivers/hid/hid-playstation.c)
- [Configuração HID_PLAYSTATION](https://github.com/torvalds/linux/blob/master/drivers/hid/Kconfig)
- [Interface de LEDs multicoloridos](https://www.kernel.org/doc/html/latest/leds/leds-class-multicolor.html)
