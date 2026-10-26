# Validación local de la herramienta, 26 de octubre de 2026

Se ejecutó el nuevo programa desde la ISO original de Anime War. No se utilizaron como entrada los directorios ya corregidos.

| Comprobación | Resultado |
|---|---|
| SHA256 de entrada | `11d91bc29bbc557c30172c6755faa0303c06dd90452dcfdafc0dd17fc602fd60` |
| SHA256 de salida | `0dfee13a6ddb02c04ef07045726e135ee4b9014da3dc337c32e74dc81cc7e52f` |
| Coincidencia con la imagen usada en el arreglo previo | Exacta |
| Datos y LBA de los 33 archivos del juego | Sin cambios |
| Directorios normalizados | 4 |
| Selección DVD antes | sector 340, longitud 589744 |
| Selección DVD después | sector 259, longitud 2048 |
| Reproducción con las instrucciones originales del selector, localmente | 259 / 2048 |
| Generación de GP4 y compilación local del nuevo paquete | Terminada |
| Auditoría del contenido dentro del PKG (ISO, configuración y componentes nativos) | SHA256 coincidentes con las entradas preparadas |
| Title ID nuevo de la validación | BTPR00001 |
| Paquete generado, bytes | 2774728704 |
| SHA256 del paquete de validación | `1e925083dc25adc2872a21b940efd2ba0e955684136fc7838eee720b224a0337` |
| Instalación/ejecución del nuevo paquete | **No realizada** |

El paquete local nuevo no se distribuye con el proyecto. La prueba en hardware de arranque, gráficos y dos jugadores sigue correspondiendo al paquete anterior 01.03 descrito en ANIME-WAR.md. No se reemplazó esa instalación funcional.

Los hooks diagnósticos de direcciones del ejecutable se excluyen de los proyectos nuevos: el perfil público solo aplica las opciones gráficas documentadas. Esto evita presentar direcciones específicas de Anime War como un parche genérico para todos los mods.
