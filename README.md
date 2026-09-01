# Personal Finance

## Propósito

Base versionable para un proyecto personal que centralizará información financiera y permitirá generar análisis y reportes.

## Estado actual

Seed inicial. Aún no contiene funcionalidad financiera, integraciones, base de datos ni infraestructura.

## Visión de largo plazo

El proyecto evolucionará hacia una aplicación y plataforma de datos para consolidar finanzas personales, almacenar la información necesaria y producir análisis útiles.

Las fuentes previstas inicialmente son archivos Excel de finanzas personales y datos obtenidos desde Gmail.

La arquitectura se definirá y ajustará según necesidades reales del proyecto. Se evita incorporar tecnologías o capas de complejidad antes de necesitarlas.

## Desarrollo

Requiere [uv](https://docs.astral.sh/uv/) y Python 3.13 (fijado en `.python-version`).

```sh
uv sync
uv run python -m unittest discover -s tests
```
