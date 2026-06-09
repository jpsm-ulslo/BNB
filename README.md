# BNB – Base Normalizada de Bens Extração de Ativos Nextbitt

## Objetivo
Extração automatizada de dados do módulo Assets do Nextbitt.

## Problema
Grid Telerik com virtualização horizontal e vertical.

## Abordagem
Iteração horizontal (colunas) + vertical (linhas).

## Processamento
Consolidação incremental por "Código".

## Validação
Filtragem de registos válidos.

## Output
CSV, Excel e checkpoints por página.

## Execução
python run_nextbitt.py

## Estrutura
client.py · login.py · filters.py · table.py

## Notas
Baseado na UI (headers visíveis), não no DOM.
