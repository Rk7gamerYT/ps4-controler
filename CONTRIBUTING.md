# Contribuir

Abra uma issue descrevendo o problema, a distribuição, a versão do kernel, a
conexão USB/Bluetooth e o modelo de controle. Remova endereços MAC e números de
série dos logs antes de compartilhar.

Para desenvolver:

```bash
./install.sh
.venv/bin/python -m unittest discover -s tests
QT_QPA_PLATFORM=offscreen .venv/bin/python app.py --demo --smoke-test
```

Envie mudanças em pull requests com uma descrição do comportamento e da validação.
Separe testes simulados de validações em hardware real. Novos controles devem ter
IDs explícitos e testes para evitar capturar teclados ou outros dispositivos.
Contribuições ao app são disponibilizadas sob a licença MIT do projeto.
