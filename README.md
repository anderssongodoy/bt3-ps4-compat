# BT3 PS4 Compat

[English](README.en.md)

Herramienta y documentaci�n para reproducir una correcci�n de compatibilidad de ISO de mods de **Budokai Tenkaichi 3** en el emulador PS2 de Sony para PS4.

**No es un conversor universal.** Un mod, Anime War vs Dragon Ball AF V2 (2022), tiene una prueba real confirmada en PS4 Fat, firmware 13.50, GoldHEN: arranque, gr�ficos y versus local para dos. El resto necesita validaci�n por mod y por revisi�n del emulador.

## Qu� aporta

- Inspecci�n ISO9660, arranque SYSTEM.CNF y modelo del selector DVD observado.
- Normalizaci�n de registros con 14 bytes System Use vac�os, sin mover archivos del juego.
- Comprobaci�n de todos los bytes: solo pueden cambiar las regiones de metadatos previstas y a�adirse el pie LIMG. Los datos y LBA de archivos del juego permanecen intactos.
- Rechazo de estructuras desconocidas, directorios sin espacio, datos System Use no reconocidos, Joliet, marcadores anteriores falsos y salidas existentes.
- Preparaci�n de un proyecto GP4 independiente usando un emulador/plantilla que el usuario ya tenga localmente y un identificador nuevo para su mod.
- Perfil gr�fico documentado y sin hooks a direcciones del ejecutable del juego.

Solo contiene c�digo propio, documentaci�n y pruebas sint�ticas. Cada usuario aporta su ISO, su plantilla local y su herramienta de construcci�n PKG. No se incluyen juegos, BIOS/ROM, ejecutables de Sony, SDK, car�tulas ni PKG.

## Uso

Python **3.10 o posterior**, sin dependencias externas. En Windows puede utilizarse `py -3` en lugar de `python`.

Inspeccionar antes de modificar:

```console
python bt3ps4.py inspect "mi-mod.iso" --report inspeccion.json
```

Crear otra imagen; el original nunca se escribe:

```console
python bt3ps4.py normalize "mi-mod.iso" --output "mi-mod-compatible.iso" --report normalizacion.json
```

Preparar un proyecto de aplicaci�n completa. `--template` debe ser el �rbol de archivos **extra�do localmente** de la revisi�n del emulador analizada; no es un PKG ni una plantilla incluida en este repositorio:

```console
python bt3ps4.py prepare-pkg "mi-mod-compatible.iso" --template "mi-wrapper-local" --output "build/mi-mod" --title-id BTMX00001 --title "Mi mod de BT3"
```

Esto produce `project.gp4`, un �rbol `app/` y `manifest.json`. La imagen se referencia sin copiarla otra vez. Use un Title ID que no pertenezca a otro juego instalado. La plantilla puede aportar iconos propios que deben sustituirse localmente si corresponden a otro t�tulo.

El proyecto **no es una actualizaci�n** para paquetes anteriores: su categor�a es `gd`. Para construirlo, indique expl�citamente su herramienta local compatible con la interfaz `img_create`:

```console
python bt3ps4.py build-pkg "build/mi-mod/project.gp4" --builder "ruta/a/mi-herramienta-pkg.exe" --output "output/mi-mod.pkg"
```

El comando ejecuta �nicamente la herramienta local que usted indique, comprueba la cabecera/Content ID y calcula SHA256. No descarga ni incluye SDK. Tambi�n puede construir el GP4 por su cuenta. Que un proyecto se genere o compile no prueba que el juego funcione en hardware.

La preparaci�n del perfil est� limitada a la revisi�n de `eboot.bin` cuyo SHA256 es:

```text
83b771a27b1ac03802e4071068885658224732a15dedaed67f120307c6e651e7
```

Otros emuladores se rechazan hasta analizarlos. La detecci�n de SLUS-21678 o SLUS-21978 es una identificaci�n por metadatos, no una prueba de equivalencia de c�digo ni de todos los mods. No se han validado otras regiones todav�a.

## Por qu� funcion�

En la rama DVD de esa revisi�n, el selector busca el primer sector con palabra inicial `0x0030` entre los sectores 257 y 999. En Anime War omite la ra�z real del sector 259, que empieza con un registro est�ndar de 34 bytes (`0x22`). Encuentra una coincidencia accidental en el ejecutable, sector 340, e interpreta 589744 bytes como tama�o de directorio.

Al ampliar los registros de directorio con 14 bytes vac�os, el registro `.` comienza por `0x30`. Los tama�os declarados se normalizan a los sectores reservados, sin cambiar los archivos ni sus posiciones. El selector pasa a elegir **259 / 2048**. Es una adaptaci�n a una heur�stica concreta del emulador; la ISO original no era necesariamente inv�lida.

El fallo de arranque y el fallo gr�fico fueron dos problemas diferentes. Despu�s se us� este conjunto GS/VU1:

```text
--gs-uprender=2x2
--gs-upscale=edgesmooth
--gs-use-clut-merge=1
--gs-kernel-cl="clutmerge"
--gs-kernel-cl-up="clutmerge2x2"
```

Se retir� `--vu1=jit-sync` y se conservaron las reglas `forceSimpleFetch` para texMode 1 y 2. **Est� confirmado el conjunto, no la responsabilidad aislada de cada opci�n.**

El segundo mando se recuper� tras usar dos usuarios activos con un mando cada uno; no se introdujo un parche de entrada. La utilidad no promete corregir todos los problemas de mandos.

## Qu� falta para decir �cualquier mod�

Validar m�s mods y regiones; comparar revisiones de emulador; estudiar im�genes con directorios mayores o en otros sectores; cubrir cambios de ELF, archivos internos, memoria y temporizaci�n; registrar batallas reales, gr�ficos, modos y dos mandos. No basta con cambiar el nombre de la ISO o su Title ID.

Informe de la prueba conocida: [docs/ANIME-WAR.md](docs/ANIME-WAR.md). Plantilla de reportes: [docs/COMPATIBILIDAD.md](docs/COMPATIBILIDAD.md).

La herramienta se contrast� con la ISO real y produjo **la misma imagen, byte por byte**, adem�s de generar y compilar un proyecto PKG independiente. [Detalle de validaci�n y l�mites](docs/VALIDACION-HERRAMIENTA.md).

## Pruebas

```console
python -m unittest discover -s tests -v
```

Las pruebas crean im�genes sint�ticas temporales. No necesitan juegos ni el emulador. El flujo de CI para Windows/Linux est� preparado; sus resultados remotos solo existir�n una vez se publique y ejecute en GitHub.

Licencia MIT para el c�digo y documentaci�n de este proyecto. Sin afiliaci�n con Sony, Bandai Namco ni equipos de mods. La t�cnica se desarroll� contrastando un paquete BT4 local que funcionaba; este proyecto no redistribuye su contenido ni se atribuye su desarrollo.
