# BT3 PS4 Compat

[English](README.en.md)

Herramienta y documentación para reproducir una corrección de compatibilidad de ISO de mods de **Budokai Tenkaichi 3** en el emulador PS2 de Sony para PS4.

**No es un conversor universal.** Un mod, Anime War vs Dragon Ball AF V2 (2022), tiene una prueba real confirmada en PS4 Fat, firmware 13.50, GoldHEN: arranque, gráficos y versus local para dos. El resto necesita validación por mod y por revisión del emulador.

## Qué aporta

- Inspección ISO9660, arranque SYSTEM.CNF y modelo del selector DVD observado.
- Normalización de registros con 14 bytes System Use vacíos, sin mover archivos del juego.
- Comprobación de todos los bytes: solo pueden cambiar las regiones de metadatos previstas y añadirse el pie LIMG. Los datos y LBA de archivos del juego permanecen intactos.
- Rechazo de estructuras desconocidas, directorios sin espacio, datos System Use no reconocidos, Joliet, marcadores anteriores falsos y salidas existentes.
- Preparación de un proyecto GP4 independiente usando un emulador/plantilla que el usuario ya tenga localmente y un identificador nuevo para su mod.
- Perfil gráfico documentado y sin hooks a direcciones del ejecutable del juego.

Solo contiene código propio, documentación y pruebas sintéticas. Cada usuario aporta su ISO, su plantilla local y su herramienta de construcción PKG. No se incluyen juegos, BIOS/ROM, ejecutables de Sony, SDK, carátulas ni PKG.

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

Preparar un proyecto de aplicación completa. `--template` debe ser el árbol de archivos **extraído localmente** de la revisión del emulador analizada; no es un PKG ni una plantilla incluida en este repositorio:

```console
python bt3ps4.py prepare-pkg "mi-mod-compatible.iso" --template "mi-wrapper-local" --output "build/mi-mod" --title-id BTMX00001 --title "Mi mod de BT3"
```

Esto produce `project.gp4`, un árbol `app/` y `manifest.json`. La imagen se referencia sin copiarla otra vez. Use un Title ID que no pertenezca a otro juego instalado. La plantilla puede aportar iconos propios que deben sustituirse localmente si corresponden a otro título.

El proyecto **no es una actualización** para paquetes anteriores: su categoría es `gd`. Para construirlo, indique explícitamente su herramienta local compatible con la interfaz `img_create`:

```console
python bt3ps4.py build-pkg "build/mi-mod/project.gp4" --builder "ruta/a/mi-herramienta-pkg.exe" --output "output/mi-mod.pkg"
```

El comando ejecuta únicamente la herramienta local que usted indique, comprueba la cabecera/Content ID y calcula SHA256. No descarga ni incluye SDK. También puede construir el GP4 por su cuenta. Que un proyecto se genere o compile no prueba que el juego funcione en hardware.

La preparación del perfil está limitada a la revisión de `eboot.bin` cuyo SHA256 es:

```text
83b771a27b1ac03802e4071068885658224732a15dedaed67f120307c6e651e7
```

Otros emuladores se rechazan hasta analizarlos. La detección de SLUS-21678 o SLUS-21978 es una identificación por metadatos, no una prueba de equivalencia de código ni de todos los mods. No se han validado otras regiones todavía.

## Por qué funcionó

En la rama DVD de esa revisión, el selector busca el primer sector con palabra inicial `0x0030` entre los sectores 257 y 999. En Anime War omite la raíz real del sector 259, que empieza con un registro estándar de 34 bytes (`0x22`). Encuentra una coincidencia accidental en el ejecutable, sector 340, e interpreta 589744 bytes como tamaño de directorio.

Al ampliar los registros de directorio con 14 bytes vacíos, el registro `.` comienza por `0x30`. Los tamaños declarados se normalizan a los sectores reservados, sin cambiar los archivos ni sus posiciones. El selector pasa a elegir **259 / 2048**. Es una adaptación a una heurística concreta del emulador; la ISO original no era necesariamente inválida.

El fallo de arranque y el fallo gráfico fueron dos problemas diferentes. Después se usó este conjunto GS/VU1:

```text
--gs-uprender=2x2
--gs-upscale=edgesmooth
--gs-use-clut-merge=1
--gs-kernel-cl="clutmerge"
--gs-kernel-cl-up="clutmerge2x2"
```

Se retiró `--vu1=jit-sync` y se conservaron las reglas `forceSimpleFetch` para texMode 1 y 2. **Está confirmado el conjunto, no la responsabilidad aislada de cada opción.**

El segundo mando se recuperó tras usar dos usuarios activos con un mando cada uno; no se introdujo un parche de entrada. La utilidad no promete corregir todos los problemas de mandos.

## Qué falta para decir «cualquier mod»

Validar más mods y regiones; comparar revisiones de emulador; estudiar imágenes con directorios mayores o en otros sectores; cubrir cambios de ELF, archivos internos, memoria y temporización; registrar batallas reales, gráficos, modos y dos mandos. No basta con cambiar el nombre de la ISO o su Title ID.

Informe de la prueba conocida: [docs/ANIME-WAR.md](docs/ANIME-WAR.md). Plantilla de reportes: [docs/COMPATIBILIDAD.md](docs/COMPATIBILIDAD.md).

La herramienta se contrastó con la ISO real y produjo **la misma imagen, byte por byte**, además de generar y compilar un proyecto PKG independiente. [Detalle de validación y límites](docs/VALIDACION-HERRAMIENTA.md).

## Pruebas

```console
python -m unittest discover -s tests -v
```

Las pruebas crean imágenes sintéticas temporales. No necesitan juegos ni el emulador. El flujo de CI para Windows/Linux está preparado; sus resultados remotos solo existirán una vez se publique y ejecute en GitHub.

Licencia MIT para el código y documentación de este proyecto. Sin afiliación con Sony, Bandai Namco ni equipos de mods. La técnica se desarrolló contrastando un paquete BT4 local que funcionaba; este proyecto no redistribuye su contenido ni se atribuye su desarrollo.
