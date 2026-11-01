# K2 Filament Control

![Creality K2](assets/spool-3d.png)

**PT** · Dashboard local para acompanhar as quatro bobinas reais do CFS, o saldo restante, o projeto aberto no MCP e o histórico de consumo da Creality K2.

**EN** · Local dashboard for the four real CFS spools, remaining stock, the project currently open in MCP, and Creality K2 consumption history.

## Features · Funcionalidades

- PT/EN language toggle.
- Four-slot CFS view with real remaining grams.
- Completed and cancelled jobs kept in history.
- Live project and print state when MCP/Creality is available.
- No manual balance correction required.

## Run locally · Executar localmente

```powershell
python server.py
```

Then open `http://127.0.0.1:8765/`.

Depois abra `ABRIR-FILAMENTOS.cmd` ou aceda ao endereço acima.

## Privacy

Runtime state, printer logs, G-code, 3MF files, videos, local IP addresses and machine-specific data are intentionally excluded from the public repository.

## Author

Fernandes · Studio Elevatio

Creality K2 is a trademark of Creality. This project is an independent local tool.

