# Rede

## Estratégia inicial

Cada VM usa duas ideias de conectividade:

- conectividade para baixar pacotes
- conectividade visível na rede local

Na prática, a v1 foi desenhada para operar com **bridged networking** como requisito principal.

## Requisitos

- a interface definida em `network.bridge_interface` deve existir no Windows
- o driver de bridge do VirtualBox deve estar funcional
- Wi-Fi pode funcionar, mas Ethernet tende a ser mais previsível

## Validação

Use:

```powershell
.\powershell\validate-network.ps1
```

## Observações

- se o bridge falhar no seu notebook, o primeiro ponto a verificar é a interface física escolhida
- dependendo do ambiente, pode ser necessário trocar o nome da interface no `cluster.yaml`
