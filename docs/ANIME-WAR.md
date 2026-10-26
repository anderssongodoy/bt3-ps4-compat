# Caso documentado: Anime War vs AF

## Confirmación en hardware

PS4 Fat, firmware 13.50, GoldHEN. Anime War vs Dragon Ball AF V2 (2022), salida local 01.03.

El usuario confirmó que personajes, escenarios y menú de pausa se ven bien y que permite jugar a dos personas. Esta es una prueba real del usuario, no una captura de vídeo remoto. No abarca todos los personajes, escenarios, modos o sesiones largas.

| Elemento | SHA256 |
|---|---|
| ISO de entrada | `11d91bc29bbc557c30172c6755faa0303c06dd90452dcfdafc0dd17fc602fd60` |
| ISO normalizada, incluido LIMG | `0dfee13a6ddb02c04ef07045726e135ee4b9014da3dc337c32e74dc81cc7e52f` |
| Revisión del emulador, eboot.bin | `83b771a27b1ac03802e4071068885658224732a15dedaed67f120307c6e651e7` |

## Evidencia del arranque

La reproducción local con las instrucciones del selector DVD mostró selección 340/589744 antes y 259/2048 después. El registro TTY de la PS4 confirmó raíz 259, longitud 2048 y detección de SLUS-21678. Se modificaron cuatro directorios ISO9660 y el tamaño de raíz en el descriptor primario. Los contenidos y LBA de archivos se conservaron.

## Evidencia de gráficos

La versión 01.01 arrancaba, pero el usuario aportó seis fotos con geometría incompleta, superficies negras y manchas en la pausa. La versión 01.02, que solo retiraba jit-sync, no se probó por separado. El perfil completo de la 01.03 está documentado en el README y fue el validado. No se puede atribuir la solución a una sola línea con la evidencia actual.

El generador público conserva las opciones gráficas y omite los hooks diagnósticos de la sesión original, que dependían de direcciones de ese ejecutable. **La preparación generada por la nueva herramienta no tiene todavía una prueba propia de ejecución en PS4**: la prueba real corresponde al paquete 01.03 anterior.

## Mandos

La sesión problemática asignaba tres usuarios a posiciones 0/1/2. Tras iniciar dos usuarios con un mando cada uno, los registros mostraron posiciones 0/1 y el usuario confirmó versus local. No hubo parche de código de mandos. Esta observación puede orientar un diagnóstico, pero no demuestra una solución universal.

## Lo que debe incluir un reporte nuevo

Modelo/FW, nombre y versión del mod, SHA256 de ISO, ID de arranque, revisión de emulador, raíz elegida antes/después, perfil, instalación correcta, batalla completa, estado gráfico y prueba de dos mandos. No publicar juegos ni volcados de memoria de usuarios.
