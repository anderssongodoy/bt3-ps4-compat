# Caso documentado: Anime War vs AF

## Confirmaci�n en hardware

PS4 Fat, firmware 13.50, GoldHEN. Anime War vs Dragon Ball AF V2 (2022), salida local 01.03.

El usuario confirm� que personajes, escenarios y men� de pausa se ven bien y que permite jugar a dos personas. Esta es una prueba real del usuario, no una captura de v�deo remoto. No abarca todos los personajes, escenarios, modos o sesiones largas.

| Elemento | SHA256 |
|---|---|
| ISO de entrada | `11d91bc29bbc557c30172c6755faa0303c06dd90452dcfdafc0dd17fc602fd60` |
| ISO normalizada, incluido LIMG | `0dfee13a6ddb02c04ef07045726e135ee4b9014da3dc337c32e74dc81cc7e52f` |
| Revisi�n del emulador, eboot.bin | `83b771a27b1ac03802e4071068885658224732a15dedaed67f120307c6e651e7` |

## Evidencia del arranque

La reproducci�n local con las instrucciones del selector DVD mostr� selecci�n 340/589744 antes y 259/2048 despu�s. El registro TTY de la PS4 confirm� ra�z 259, longitud 2048 y detecci�n de SLUS-21678. Se modificaron cuatro directorios ISO9660 y el tama�o de ra�z en el descriptor primario. Los contenidos y LBA de archivos se conservaron.

## Evidencia de gr�ficos

La versi�n 01.01 arrancaba, pero el usuario aport� seis fotos con geometr�a incompleta, superficies negras y manchas en la pausa. La versi�n 01.02, que solo retiraba jit-sync, no se prob� por separado. El perfil completo de la 01.03 est� documentado en el README y fue el validado. No se puede atribuir la soluci�n a una sola l�nea con la evidencia actual.

El generador p�blico conserva las opciones gr�ficas y omite los hooks diagn�sticos de la sesi�n original, que depend�an de direcciones de ese ejecutable. **La preparaci�n generada por la nueva herramienta no tiene todav�a una prueba propia de ejecuci�n en PS4**: la prueba real corresponde al paquete 01.03 anterior.

## Mandos

La sesi�n problem�tica asignaba tres usuarios a posiciones 0/1/2. Tras iniciar dos usuarios con un mando cada uno, los registros mostraron posiciones 0/1 y el usuario confirm� versus local. No hubo parche de c�digo de mandos. Esta observaci�n puede orientar un diagn�stico, pero no demuestra una soluci�n universal.

## Lo que debe incluir un reporte nuevo

Modelo/FW, nombre y versi�n del mod, SHA256 de ISO, ID de arranque, revisi�n de emulador, ra�z elegida antes/despu�s, perfil, instalaci�n correcta, batalla completa, estado gr�fico y prueba de dos mandos. No publicar juegos ni volcados de memoria de usuarios.
