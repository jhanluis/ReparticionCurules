from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from math import floor
from collections import defaultdict, Counter

# @dataclass
# class Config:
#     # Lista de regiones (circunscripciones). 
#     # Por defecto crea 5: "Circ-1", "Circ-2", ..., "Circ-5".
#     regiones: List[str] = field(default_factory=lambda: [f"Circ-{i}" for i in range(1, 6)])
    
#     # Número de asientos (curules) que se asignan en cada región
#     asientos_por_region: int = 40
    
#     # Umbral nacional mínimo de votos que debe tener un partido para acceder al reparto (3%)
#     umbral_nacional: float = 0.03  

#     # Bandera para indicar si se aplica el tope de sobrerrepresentación
#     aplicar_tope_sobrerrep: bool = True
    
#     # Margen máximo de sobrerrepresentación permitido (+8%)
#     margen_tope: float = 0.08      
    
#     # Total de asientos en la cámara (500 por defecto)
#     total_camara: int = 500

# @dataclass
# class DatosEntrada:
#     # Votos por región:
#     # Estructura: {region: {partido: votos_validos_partido_en_region}}
#     # Ejemplo: {"Circ-1": {"PAN": 100000, "PRI": 80000, "Morena": 120000}}
#     votos_region: Dict[str, Dict[str, int]]
    
#     # Votación nacional efectiva (VNE) por partido:
#     # Estructura: {partido: votos_totales}
#     # Ejemplo: {"PAN": 195000, "PRI": 150000, "Morena": 250000}
#     vne_nacional: Dict[str, int]
    
#     # Diputaciones de mayoría relativa (MR) ya ganadas por partido:
#     # Estructura: {partido: escaños_MR}
#     # Ejemplo: {"PAN": 80, "PRI": 40, "Morena": 100}
#     distritos_mr: Dict[str, int]

# @dataclass
# class ResultadoRegion:
#     # Asignación final de asientos en la región:
#     # {partido: número_de_escaños}
#     asientos: Dict[str, int]
    
#     # Ranking de cocientes usado para asignar asientos:
#     # Lista de tuplas en orden descendente:
#     # [(cociente, partido, divisor_usado)]
#     ranking: List[Tuple[float, str, int]]

# @dataclass
# class ResultadoNacional:
#     # Configuración usada para el cálculo (umbral, tope, etc.)
#     config: Config
    
#     # Partidos que superaron el umbral nacional y fueron elegibles
#     elegibles: List[str]
    
#     # Resultados detallados por región
#     # {region: ResultadoRegion}
#     asignacion_por_region: Dict[str, ResultadoRegion]
    
#     # Diputaciones de representación proporcional por partido
#     rp_nacional_por_partido: Dict[str, int]
    
#     # Total de diputaciones por partido (MR + RP)
#     total_por_partido: Dict[str, int]
    
#     # Tope de sobrerrepresentación aplicado por partido (si aplica)
#     tope_por_partido: Dict[str, int]
    
#     # Notas y observaciones del cálculo (ejemplo: ajustes por tope)
#     notas: List[str] = field(default_factory=list)

# def _calcular_elegibles(vne: Dict[str, int], umbral: float) -> List[str]:
#     # Calcula el total de votos (suma de todos los valores en el diccionario)
#     total = sum(vne.values())
    
#     # Si el total es cero o negativo (caso raro, pero previene división por cero),
#     # no hay partidos elegibles → se regresa una lista vacía
#     if total <= 0:
#         return []
    
#     # Devuelve una lista con los partidos (claves del diccionario)
#     # que superan o igualan el umbral de votos respecto al total.
#     # Ejemplo: si umbral = 0.03, solo se quedan los partidos con ≥ 3% del total.
#     return [p for p, v in vne.items() if v / total >= umbral]

# def _ranking(votos, asientos, elegibles):
#     """
#     Calcula el ranking de cocientes para repartir asientos.

#     Parámetros:
#     votos: diccionario {partido -> votos obtenidos}.
#     asientos: número total de escaños a repartir.
#     elegibles: lista de partidos que pasan el umbral y pueden competir.

#     Retorna:
#     Lista de tuplas (cociente, partido, divisor), ordenada de mayor a menor.
#     """

#     # Lista donde se almacenan todos los cocientes generados
#     ranking = []

#     # Recorremos cada partido con su número de votos
#     for partido, v in votos.items():
#         # Si el partido no está en la lista de elegibles, se ignora
#         if partido not in elegibles:
#             continue
#         # Para cada divisor desde 1 hasta el número de asientos,
#         # calculamos el cociente y lo guardamos en la lista
#         for d in range(1, asientos + 1):
#             ranking.append((v / d if d > 0 else 0.0, partido, d))

#     # Copiamos los votos originales para usarlos en los desempates
#     votos_base = votos.copy()

#     # Ordenamos el ranking con las siguientes reglas:
#     # 1. Cociente en orden descendente.
#     # 2. Votos base del partido en orden descendente (si hay empate en cocientes).
#     # 3. (opcional) Nombre del partido en orden alfabético como último desempate.
#     ranking.sort(
#         key=lambda x: (x[0], votos_base[x[1]], x[1]),
#         reverse=True
#     )

#     # Se devuelve la lista completa de cocientes ordenados
#     return ranking

# def _asignar_region(votos_region, asientos, elegibles):
#     """
#     Asigna escaños en una región usando el método D'Hondt.

#     Parámetros:
#     votos_region: diccionario {partido -> votos obtenidos en la región}.
#     asientos: número total de escaños a repartir en la región.
#     elegibles: lista de partidos que pasan el umbral y pueden competir.

#     Retorna:
#     Objeto ResultadoRegion con:
#         - asientos: diccionario {partido -> escaños asignados}.
#         - ranking: lista completa de cocientes generados por D'Hondt.
#     """

#     # Calculamos el ranking de cocientes para los partidos elegibles
#     ranking = _ranking(votos_region, asientos, elegibles)

#     # Contador de asientos asignados por partido
#     asignados = Counter()

#     # Índice para recorrer el ranking
#     i = 0

#     # Lista con las asignaciones hechas (para trazabilidad)
#     picks = []

#     # Mientras no se repartan todos los asientos y queden cocientes disponibles
#     while sum(asignados.values()) < asientos and i < len(ranking):
#         # Tomamos el cociente, partido y divisor de la posición actual
#         q, partido, div = ranking[i]

#         # Asignamos un asiento al partido correspondiente
#         asignados[partido] += 1

#         # Guardamos el detalle de la asignación
#         picks.append((q, partido, div))

#         # Avanzamos al siguiente en el ranking
#         i += 1

#     # Se devuelve el resultado con:
#     # - el diccionario de asientos asignados
#     # - el ranking completo (sirve para revisiones o reasignaciones posteriores)
#     return ResultadoRegion(asientos=dict(asignados), ranking=ranking)

# def _agrupar_asignacion_inicial(votos_region, config, elegibles):
#     """
#     Realiza la asignación inicial de escaños por región usando el método D'Hondt.

#     Parámetros:
#     votos_region: diccionario {region -> {partido -> votos en esa región}}.
#         Ejemplo:
#         {
#             "Norte": {"PAN": 10000, "PRI": 8000, "MORENA": 12000},
#             "Sur":   {"PAN":  6000, "PRI": 9000, "MORENA":  7000}
#         }

#     config: objeto Config que contiene parámetros generales de la elección.
#         - config.asientos_por_region: número de asientos a repartir en cada región.

#     elegibles: lista de partidos que pasan el umbral y pueden competir.

#     Retorna:
#     Diccionario {region -> ResultadoRegion}, donde cada ResultadoRegion contiene:
#         - asientos: dict {partido -> escaños asignados en la región}.
#         - ranking: lista completa de cocientes generados en esa región.
#     """

#     # Diccionario donde se guardarán los resultados por región
#     resultados = {}

#     # Recorremos cada región y sus votos
#     for region, votos in votos_region.items():
#         # Para cada región aplicamos la asignación D'Hondt
#         resultados[region] = _asignar_region(
#             votos,
#             config.asientos_por_region,
#             elegibles
#         )

#     # Devolvemos el mapeo completo: {region -> ResultadoRegion}
#     return resultados

# def _suma_rp_nacional(asignacion_por_region):
#     """
#     Suma los resultados de representación proporcional (RP) a nivel nacional.

#     Parámetros:
#     asignacion_por_region: diccionario {region -> ResultadoRegion}.
#         Cada ResultadoRegion contiene, entre otras cosas:
#             - asientos: dict {partido -> número de escaños asignados en esa región}.

#     Retorna:
#     Diccionario {partido -> total de escaños a nivel nacional}.
#     """

#     # Contador para acumular los asientos de todos los partidos
#     tot = Counter()

#     # Recorremos los resultados de cada región
#     for r in asignacion_por_region.values():
#         # Sumamos los asientos de cada partido en esa región
#         for p, n in r.asientos.items():
#             tot[p] += n

#     # Convertimos el Counter en un diccionario normal antes de regresar
#     return dict(tot)

# def _calcular_topes(vne, config):
#     """
#     Calcula los topes máximos de escaños por partido según las reglas de sobrerrepresentación.

#     Parámetros:
#     vne: diccionario {partido -> votos no eliminados}.
#     config: objeto Config con parámetros generales, debe incluir:
#         - total_camara: número total de escaños de la cámara.
#         - margen_tope: margen adicional permitido sobre el porcentaje de votos.
#         - aplicar_tope_sobrerrep: booleano; si True se aplica el tope de sobrerrepresentación.

#     Retorna:
#     Diccionario {partido -> número máximo de escaños que puede obtener}.
#     """

#     # Suma total de votos válidos (no eliminados)
#     total_votos = sum(vne.values())

#     # Diccionario de resultados
#     topes = {}

#     # Recorremos cada partido y sus votos
#     for p, v in vne.items():
#         # Proporción de votos que le corresponden (entre 0 y 1)
#         share = (v / total_votos) if total_votos > 0 else 0.0

#         # Límite máximo permitido:
#         #   - Si se aplica tope de sobrerrepresentación → share + margen_tope
#         #   - Si no se aplica → hasta el 100% (1.0 adicional)
#         max_pct = share + (config.margen_tope if config.aplicar_tope_sobrerrep else 1.0)

#         # Se calcula el número máximo de escaños como el piso de ese porcentaje
#         topes[p] = floor(max_pct * config.total_camara)

#     # Devolvemos el diccionario {partido -> tope máximo de escaños}
#     return topes

# def _remover_rp_de_partido_en_region(res_region, partido, a_remover):
#     """
#     Quita 'a_remover' escaños de representación proporcional (RP) a un partido en una región,
#     empezando por los últimos obtenidos (los de menor cociente).
    
#     Parámetros:
#     res_region: objeto ResultadoRegion con:
#         - asientos: dict {partido -> número de escaños asignados}.
#         - ranking: lista de cocientes (cociente, partido, divisor), ordenada de mayor a menor.
#     partido: nombre del partido al que se le quitarán escaños.
#     a_remover: cantidad de escaños a remover.
    
#     Retorna:
#     Número de escaños efectivamente removidos (puede ser menor a 'a_remover' si no había tantos).
#     """

#     # Número total de asientos asignados en la región
#     asientos_region = sum(res_region.asientos.values())

#     # Picks = primeras 'asientos_region' posiciones del ranking,
#     # que corresponden a los escaños realmente asignados en esa región
#     picks = res_region.ranking[:asientos_region]

#     # Obtenemos los índices en los que este partido tiene escaños dentro de los picks
#     indices_partido = [i for i, (q, p, d) in enumerate(picks) if p == partido]

#     # Contador de cuántos escaños removimos efectivamente
#     removidos = 0

#     # Recorremos los índices del partido en orden inverso (del último escaño asignado al primero)
#     for idx in reversed(indices_partido):
#         if removidos >= a_remover:
#             break
#         # Reducimos en 1 el número de asientos del partido
#         res_region.asientos[partido] -= 1
#         removidos += 1

#     # Si el partido ya no tiene escaños asignados, lo eliminamos del diccionario
#     if res_region.asientos.get(partido, 0) <= 0:
#         res_region.asientos.pop(partido, None)

#     # Devolvemos cuántos escaños se removieron efectivamente
#     return removidos

# def _siguiente_en_fila(region, ya_asignados, elegibles):
#     """
#     Obtiene las siguientes opciones de escaños disponibles en una región,
#     es decir, aquellos cocientes que todavía no han sido asignados.

#     Parámetros:
#     region: objeto ResultadoRegion con:
#         - asientos: dict {partido -> número de escaños ya asignados en la región}.
#         - ranking: lista de cocientes (cociente, partido, divisor), ordenada de mayor a menor.
#     ya_asignados: dict {partido -> número de escaños ya considerados}, 
#                   aunque en esta implementación no se usa directamente.
#     elegibles: lista de partidos que pasan el umbral y pueden competir.

#     Retorna:
#     Lista de tuplas (partido, cociente), ordenada de mayor a menor cociente,
#     que representan las siguientes opciones disponibles para asignación.
#     """

#     # Número de asientos ya ocupados en la región
#     asientos_region = sum(region.asientos.values())

#     # Conjunto para marcar los cocientes ya tomados
#     taken = set()

#     # Los cocientes ya asignados corresponden a los primeros 'asientos_region' del ranking
#     for q, p, d in region.ranking[:asientos_region]:
#         taken.add((p, d))

#     # Lista de posibles siguientes asignaciones
#     opciones = []

#     # Recorremos el resto del ranking (a partir del primer cociente NO asignado aún)
#     for q, p, d in region.ranking[asientos_region:]:
#         # Si el partido no es elegible, lo saltamos
#         if p not in elegibles:
#             continue
#         # Si este cociente ya fue tomado, lo saltamos
#         if (p, d) in taken:
#             continue
#         # Agregamos la opción como (partido, cociente)
#         opciones.append((p, q))

#     # Ordenamos las opciones en orden descendente por cociente
#     opciones.sort(key=lambda x: x[1], reverse=True)

#     # Devolvemos la lista de siguientes candidatos
#     return opciones

# def asignar_rp(datos, config=None):
#     """
#     Asigna 200 diputaciones de Representación Proporcional (RP) aplicando,
#     si la configuración lo indica, el tope de sobrerrepresentación.

#     Entradas:
#       - datos.votos_region: {region: {partido: votos_validos_en_region}}
#       - datos.vne_nacional: {partido: votos_VNE} (¡ya depurados!)
#       - datos.distritos_mr: {partido: escaños_MR}
#       - config: objeto Config con parámetros generales. Por defecto:
#           * 5 regiones de 40 escaños cada una
#           * Umbral nacional: 3%
#           * Tope de sobrerrepresentación: +8%

#     Salidas:
#       Objeto ResultadoNacional con:
#         - asignacion_por_region: resultados por región (ResultadoRegion)
#         - rp_nacional_por_partido: curules de RP por partido
#         - total_por_partido: MR + RP
#         - tope_por_partido (si aplica)
#         - elegibles y notas (información adicional)
#     """

#     # Configuración por defecto si no se pasa una
#     cfg = config or Config()

#     # 1) Calcular partidos elegibles a nivel nacional
#     elegibles = _calcular_elegibles(datos.vne_nacional, cfg.umbral_nacional)

#     # 2) Asignación inicial con D’Hondt en cada región
#     asignacion_por_region = _agrupar_asignacion_inicial(datos.votos_region, cfg, elegibles)

#     # Suma de RP por partido a nivel nacional
#     rp_nacional = _suma_rp_nacional(asignacion_por_region)

#     # 3) Totales iniciales = MR + RP
#     total_por_partido = Counter(datos.distritos_mr) + Counter(rp_nacional)

#     # Listado de notas/advertencias
#     notas = []
#     # Diccionario de topes por partido
#     tope_por_partido = {}

#     # Si está activado el tope de sobrerrepresentación
#     if cfg.aplicar_tope_sobrerrep:
#         # 4) Calcular topes nacionales por partido
#         tope_por_partido = _calcular_topes(datos.vne_nacional, cfg)

#         # 5) Ajustes si algún partido supera su tope

#         # --- Caso 1: partidos que ya exceden el tope solo con MR ---
#         # En este caso, su RP se elimina por completo
#         liberar_por_region = Counter()
#         for p, total in total_por_partido.items():
#             tope = tope_por_partido.get(p, 10**9)
#             mr = datos.distritos_mr.get(p, 0)
#             if mr >= tope:
#                 # Se eliminan todas sus curules de RP
#                 a_quitar = rp_nacional.get(p, 0)
#                 if a_quitar > 0:
#                     # Se van quitando de cada región, empezando por los escaños más débiles
#                     for region in asignacion_por_region.keys():
#                         if a_quitar <= 0:
#                             break
#                         r = asignacion_por_region[region]
#                         en_region = r.asientos.get(p, 0)
#                         if en_region > 0:
#                             rem = _remover_rp_de_partido_en_region(r, p, min(en_region, a_quitar))
#                             liberar_por_region[region] += rem
#                             a_quitar -= rem
#                     # Se ajusta su RP nacional
#                     rp_nacional[p] = 0
#                 # Totales actualizados: solo MR
#                 total_por_partido[p] = mr

#         # --- Caso 2: partidos que exceden el tope con MR + RP ---
#         for p, total in list(total_por_partido.items()):
#             tope = tope_por_partido.get(p, 10**9)
#             if total > tope:
#                 excedente = total - tope
#                 # Se recorta RP en la cantidad de excedente
#                 a_quitar = min(excedente, rp_nacional.get(p, 0))
#                 if a_quitar > 0:
#                     for region in asignacion_por_region.keys():
#                         if a_quitar <= 0:
#                             break
#                         r = asignacion_por_region[region]
#                         en_region = r.asientos.get(p, 0)
#                         if en_region > 0:
#                             rem = _remover_rp_de_partido_en_region(r, p, min(en_region, a_quitar))
#                             liberar_por_region[region] += rem
#                             a_quitar -= rem
#                     # Ajustar RP y totales
#                     rp_nacional[p] -= (excedente - a_quitar if a_quitar < excedente else excedente)
#                     total_por_partido[p] = datos.distritos_mr.get(p, 0) + rp_nacional.get(p, 0)

#         # 6) Reasignar los escaños liberados en cada región
#         for region, libres in liberar_por_region.items():
#             r = asignacion_por_region[region]
#             # Opciones de nuevos cocientes disponibles
#             opciones = _siguiente_en_fila(r, r.asientos, elegibles)
#             idx = 0
#             while libres > 0 and idx < len(opciones):
#                 partido, cociente = opciones[idx]
#                 idx += 1
#                 # Revisar tope antes de asignar
#                 if cfg.aplicar_tope_sobrerrep:
#                     tope = tope_por_partido.get(partido, 10**9)
#                     if total_por_partido.get(partido, 0) + 1 > tope:
#                         continue
#                 # Asignar un asiento al partido
#                 r.asientos[partido] = r.asientos.get(partido, 0) + 1
#                 rp_nacional[partido] = rp_nacional.get(partido, 0) + 1
#                 total_por_partido[partido] = datos.distritos_mr.get(partido, 0) + rp_nacional.get(partido, 0)
#                 libres -= 1
#             if libres > 0:
#                 # Si sobran asientos no reasignables, se deja nota
#                 notas.append(f"No fue posible reasignar {libres} asientos en {region} por restricciones de tope/umbral.")

#     # Recalcular resultados finales y limpiar diccionarios
#     rp_nacional = {p: int(n) for p, n in rp_nacional.items() if n > 0}
#     total_por_partido = {p: int(n) for p, n in total_por_partido.items() if n > 0}

#     # Empaquetar en ResultadoNacional
#     return ResultadoNacional(
#         config=cfg,
#         elegibles=elegibles,
#         asignacion_por_region=asignacion_por_region,
#         rp_nacional_por_partido=rp_nacional,
#         total_por_partido=total_por_partido,
#         tope_por_partido=tope_por_partido,
#         notas=notas
#     )

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from collections import Counter
from math import floor

# =========================
#   CLASES DE DATOS
# =========================

@dataclass
class Config:
    # Lista de regiones (circunscripciones).
    # Por defecto crea 5: "Circ-1", "Circ-2", ..., "Circ-5".
    regiones: List[str] = field(default_factory=lambda: [f"Circ-{i}" for i in range(1, 6)])

    # Número de asientos (curules) que se asignan en cada región
    asientos_por_region: int = 40

    # Umbral nacional mínimo de votos que debe tener un partido para acceder al reparto (3%)
    umbral_nacional: float = 0.03

    # Bandera para indicar si se aplica el tope de sobrerrepresentación
    aplicar_tope_sobrerrep: bool = True

    # Margen máximo de sobrerrepresentación permitido (+8%)
    margen_tope: float = 0.08

    # Total de asientos en la cámara (500 por defecto)
    total_camara: int = 500


@dataclass
class DatosEntrada:
    # Votos por región:
    # {region: {partido: votos_validos_partido_en_region}}
    votos_region: Dict[str, Dict[str, int]]

    # Votación nacional efectiva (VNE) por partido:
    # {partido: votos_totales}
    vne_nacional: Dict[str, int]

    # Diputaciones de mayoría relativa (MR) ya ganadas por partido:
    # {partido: escaños_MR}
    distritos_mr: Dict[str, int]


@dataclass
class ResultadoRegion:
    # Asignación final de asientos en la región: {partido: número_de_escaños}
    asientos: Dict[str, int]

    # Ranking usado para asignar asientos:
    # Lista de tuplas en **orden de obtención**:
    # [(score, partido, indice_del_asiento_del_partido)]
    # * Para picks por cuota entera: score = v/cuota
    # * Para picks por restos: score = resto (v - floor(v/cuota)*cuota)
    ranking: List[Tuple[float, str, int]]


@dataclass
class ResultadoNacional:
    # Configuración usada para el cálculo (umbral, tope, etc.)
    config: Config

    # Partidos que superaron el umbral nacional y fueron elegibles
    elegibles: List[str]

    # Resultados detallados por región: {region: ResultadoRegion}
    asignacion_por_region: Dict[str, ResultadoRegion]

    # Diputaciones de representación proporcional por partido
    rp_nacional_por_partido: Dict[str, int]

    # Total de diputaciones por partido (MR + RP)
    total_por_partido: Dict[str, int]

    # Tope de sobrerrepresentación aplicado por partido (si aplica)
    tope_por_partido: Dict[str, int]

    # Notas y observaciones del cálculo (ej.: ajustes por tope)
    notas: List[str] = field(default_factory=list)


# =========================
#   FUNCIONES AUXILIARES
# =========================

def _calcular_elegibles(vne: Dict[str, int], umbral: float) -> List[str]:
    """
    Devuelve la lista de partidos con proporción de votos >= umbral.
    """
    total = sum(vne.values())
    if total <= 0:
        return []
    return [p for p, v in vne.items() if (v / total) >= umbral]


def _cuota_hare(votos: Dict[str, int], asientos: int) -> float:
    """
    Cuota de Hare (cociente natural): total_votos / asientos.
    Se calcula solo con partidos elegibles (ya filtra quien llame a esta función).
    """
    total = sum(votos.values())
    if asientos <= 0 or total <= 0:
        return 0.0
    return total / asientos


# =========================
#   RANKING (RESTO MAYOR)
# =========================

def _ranking(votos: Dict[str, int], asientos: int, elegibles: List[str]) -> List[Tuple[float, str, int]]:
    """
    Construye el ranking en **orden de obtención** para Resto Mayor

    1) Asientos por **parte entera**: floor(v / cuota). Se agregan primero al ranking;
       para trazabilidad, se añade un pick por cada asiento con score = v/cuota.

    2) Asientos por **restos más grandes**: se reparten los asientos restantes
       uno por uno. Orden de desempate: resto desc, votos_base desc, nombre asc.

    Devuelve tuplas (score, partido, d):
      - score: v/cuota (cuota entera) o resto (en fase de restos).
      - d: índice de asiento acumulado por partido (1..k).
    """
    # Filtrar solo elegibles
    votos_elegibles = {p: v for p, v in votos.items() if p in elegibles}

    cuota = _cuota_hare(votos_elegibles, asientos)
    if cuota <= 0:
        return []

    # 1) Parte entera
    base = {p: int(v // cuota) for p, v in votos_elegibles.items()}
    asignados_cuota = sum(base.values())
    restantes = max(0, asientos - asignados_cuota)

    # 2) Restos
    restos = {p: (v - base[p] * cuota) for p, v in votos_elegibles.items()}

    # 3) Ranking en orden de obtención
    ranking: List[Tuple[float, str, int]] = []
    d_actual = {p: 0 for p in votos_elegibles}

    # 3.a) Primero, picks por cuota entera (score informativo = v/cuota)
    for p, v in votos_elegibles.items():
        for _ in range(base[p]):
            d_actual[p] += 1
            ranking.append(((v / cuota) if cuota > 0 else 0.0, p, d_actual[p]))

    # 3.b) Luego, repartir los 'restantes' por restos más grandes
    if restantes > 0:
        # candidatos: (resto, votos_base, partido)
        candidatos = [(restos[p], votos_elegibles[p], p) for p in votos_elegibles]
        # Orden: resto desc, votos_base desc, nombre asc
        candidatos.sort(key=lambda t: (t[0], t[1], t[2]), reverse=True)

        idx = 0
        n = len(candidatos)
        while restantes > 0 and n > 0:
            resto, votos_base, partido = candidatos[idx]
            d_actual[partido] += 1
            ranking.append((resto, partido, d_actual[partido]))
            base[partido] += 1
            restantes -= 1
            idx = (idx + 1) % n

    return ranking


# =========================
#   ASIGNACIÓN REGIONAL
# =========================

def _asignar_region(votos_region: Dict[str, int], asientos: int, elegibles: List[str]) -> ResultadoRegion:
    """
    Asigna escaños en una región con **Resto Mayor (Hare)**:
      - Construye ranking en orden de obtención.
      - Toma los primeros 'asientos' del ranking como asignaciones efectivas.
    """
    ranking = _ranking(votos_region, asientos, elegibles)

    asignados: Dict[str, int] = {}
    for score, partido, d in ranking[:asientos]:
        asignados[partido] = asignados.get(partido, 0) + 1

    return ResultadoRegion(asientos=asignados, ranking=ranking)


def _agrupar_asignacion_inicial(votos_region: Dict[str, Dict[str, int]], config: Config, elegibles: List[str]) -> Dict[str, ResultadoRegion]:
    """
    Aplica la asignación por Resto Mayor a **cada región** y devuelve {region -> ResultadoRegion}.
    """
    resultados: Dict[str, ResultadoRegion] = {}
    for region, votos in votos_region.items():
        resultados[region] = _asignar_region(votos, config.asientos_por_region, elegibles)
    return resultados


def _suma_rp_nacional(asignacion_por_region: Dict[str, ResultadoRegion]) -> Dict[str, int]:
    """
    Suma los escaños RP de todas las regiones → {partido -> total RP nacional}.
    """
    tot = Counter()
    for r in asignacion_por_region.values():
        for p, n in r.asientos.items():
            tot[p] += n
    return dict(tot)


def _calcular_topes(vne: Dict[str, int], config: Config) -> Dict[str, int]:
    """
    Tope por partido = floor( (share + margen) * total_camara ), si aplicar_tope_sobrerrep.
    Si no aplica, equivalente a permitir hasta 100% (share + 1.0).
    """
    total_votos = sum(vne.values())
    topes: Dict[str, int] = {}
    for p, v in vne.items():
        share = (v / total_votos) if total_votos > 0 else 0.0
        max_pct = share + (config.margen_tope if config.aplicar_tope_sobrerrep else 1.0)
        topes[p] = floor(max_pct * config.total_camara)
    return topes


def _remover_rp_de_partido_en_region(res_region: ResultadoRegion, partido: str, a_remover: int) -> int:
    """
    Quita 'a_remover' escaños RP de 'partido' en la región,
    empezando por los **últimos obtenidos** (menor prioridad).
    Devuelve cuántos removió efectivamente.
    """
    # Número de asientos efectivamente asignados en la región
    asientos_region = sum(res_region.asientos.values())

    # Picks realmente asignados (en orden de obtención)
    picks = res_region.ranking[:asientos_region]

    # Índices de los picks que pertenecen al partido
    indices_partido = [i for i, (_q, p, _d) in enumerate(picks) if p == partido]

    removidos = 0
    for idx in reversed(indices_partido):
        if removidos >= a_remover:
            break
        res_region.asientos[partido] -= 1
        removidos += 1

    if res_region.asientos.get(partido, 0) <= 0:
        res_region.asientos.pop(partido, None)

    return removidos


def _siguiente_en_fila(region: ResultadoRegion, ya_asignados: Dict[str, int], elegibles: List[str]) -> List[Tuple[str, float]]:
    """
    Regresa una lista [(partido, score)] de los siguientes picks NO asignados aún en la región,
    en orden descendente del score.
    """
    asientos_region = sum(region.asientos.values())
    taken = set()
    for q, p, d in region.ranking[:asientos_region]:
        taken.add((p, d))

    opciones: List[Tuple[str, float]] = []
    for q, p, d in region.ranking[asientos_region:]:
        if p not in elegibles:
            continue
        if (p, d) in taken:
            continue
        opciones.append((p, q))

    opciones.sort(key=lambda t: t[1], reverse=True)
    return opciones


# =========================
#   PIPELINE NACIONAL RP
# =========================

def asignar_rp(datos: DatosEntrada, config: Optional[Config] = None) -> ResultadoNacional:
    """
    Asigna 200 diputaciones de RP (5 regiones x 40) con **Resto Mayor (Hare)** y,
    si corresponde, aplica el tope de sobrerrepresentación (+8% por defecto).

    Entradas:
      - datos.votos_region: {region: {partido: votos_validos_en_region}}
      - datos.vne_nacional: {partido: votos_VNE} (ya depurados)
      - datos.distritos_mr: {partido: escaños_MR}
      - config: Config (por defecto 5 regiones, 40 c/u, umbral 3%, tope +8%)

    Salidas:
      ResultadoNacional con:
        - asignacion_por_region: {region: ResultadoRegion}
        - rp_nacional_por_partido: {partido: RP}
        - total_por_partido: {partido: MR + RP}
        - tope_por_partido (si aplica)
        - elegibles y notas
    """
    cfg = config or Config()

    # 1) Umbral nacional
    elegibles = _calcular_elegibles(datos.vne_nacional, cfg.umbral_nacional)

    # 2) Asignación inicial por Resto Mayor (Hare) en cada región
    asignacion_por_region = _agrupar_asignacion_inicial(datos.votos_region, cfg, elegibles)
    rp_nacional = _suma_rp_nacional(asignacion_por_region)

    # 3) Totales iniciales
    total_por_partido = Counter(datos.distritos_mr) + Counter(rp_nacional)

    notas: List[str] = []
    tope_por_partido: Dict[str, int] = {}

    if cfg.aplicar_tope_sobrerrep:
        # 4) Calcular topes nacionales
        tope_por_partido = _calcular_topes(datos.vne_nacional, cfg)

        # 5) Identificar excesos y recortar RP si es necesario
        liberar_por_region = Counter()

        # (a) Partidos que ya exceden el tope SOLO con MR → su RP va a cero
        for p, total in list(total_por_partido.items()):
            tope = tope_por_partido.get(p, 10**9)
            mr = datos.distritos_mr.get(p, 0)
            if mr >= tope:
                a_quitar = rp_nacional.get(p, 0)
                if a_quitar > 0:
                    # Quitar de regiones empezando por los últimos obtenidos
                    for region in asignacion_por_region.keys():
                        if a_quitar <= 0:
                            break
                        r = asignacion_por_region[region]
                        en_region = r.asientos.get(p, 0)
                        if en_region > 0:
                            rem = _remover_rp_de_partido_en_region(r, p, min(en_region, a_quitar))
                            liberar_por_region[region] += rem
                            a_quitar -= rem
                    rp_nacional[p] = 0
                total_por_partido[p] = mr  # sin RP

        # (b) Partidos que exceden tope con MR+RP → recortar el excedente de RP
        for p, total in list(total_por_partido.items()):
            tope = tope_por_partido.get(p, 10**9)
            if total > tope:
                excedente = total - tope
                a_quitar = min(excedente, rp_nacional.get(p, 0))
                if a_quitar > 0:
                    for region in asignacion_por_region.keys():
                        if a_quitar <= 0:
                            break
                        r = asignacion_por_region[region]
                        en_region = r.asientos.get(p, 0)
                        if en_region > 0:
                            rem = _remover_rp_de_partido_en_region(r, p, min(en_region, a_quitar))
                            liberar_por_region[region] += rem
                            a_quitar -= rem
                    # Ajustar RP y totales
                    rp_nacional[p] = rp_nacional.get(p, 0) - (excedente if a_quitar >= excedente else (excedente - a_quitar))
                    if rp_nacional[p] < 0:
                        rp_nacional[p] = 0
                    total_por_partido[p] = datos.distritos_mr.get(p, 0) + rp_nacional.get(p, 0)

        # 6) Reasignar escaños liberados por región a “siguientes en la fila”, evitando rebasar topes
        for region, libres in liberar_por_region.items():
            r = asignacion_por_region[region]
            opciones = _siguiente_en_fila(r, r.asientos, elegibles)
            idx = 0
            while libres > 0 and idx < len(opciones):
                partido, score = opciones[idx]
                idx += 1
                # Checar tope
                tope = tope_por_partido.get(partido, 10**9)
                if total_por_partido.get(partido, 0) + 1 > tope:
                    continue
                # Asignar
                r.asientos[partido] = r.asientos.get(partido, 0) + 1
                rp_nacional[partido] = rp_nacional.get(partido, 0) + 1
                total_por_partido[partido] = datos.distritos_mr.get(partido, 0) + rp_nacional.get(partido, 0)
                libres -= 1
            if libres > 0:
                notas.append(f"No fue posible reasignar {libres} asientos en {region} por restricciones de tope/umbral.")

    # Limpieza de salidas
    rp_nacional = {p: int(n) for p, n in rp_nacional.items() if n > 0}
    total_por_partido = {p: int(n) for p, n in total_por_partido.items() if n > 0}

    return ResultadoNacional(
        config=cfg,
        elegibles=elegibles,
        asignacion_por_region=asignacion_por_region,
        rp_nacional_por_partido=rp_nacional,
        total_por_partido=total_por_partido,
        tope_por_partido=tope_por_partido,
        notas=notas
    )



import streamlit as st
import pandas as pd

# ---------------------------------------------------
# IMPORTA tus funciones/clases ya definidas:
# from tu_modulo import Config, DatosEntrada, asignar_rp
# ---------------------------------------------------

st.set_page_config(page_title="Asignación de Curules RP (MX)", layout="wide")
st.title("📊 Asignación de Curules por Representación Proporcional (MX)")

# ---------------------------
# PRESET (según tu mensaje)
# ---------------------------
PRESET_VOTOS_REGION = {
    "PRIMERA": {"PAN": 1886007, "PRI": 1162528, "PT": 517448, "PVEM": 704142, "MC": 1774320, "MORENA": 4519464},
    "SEGUNDA": {"PAN": 2682634, "PRI": 1521683, "PT": 417610, "PVEM": 997339, "MC": 1330554, "MORENA": 3722803},
    "TERCERA": {"PAN": 1320664, "PRI": 945965, "PT": 810826, "PVEM": 1266771, "MC": 960131, "MORENA": 5433356},
    "CUARTA":  {"PAN": 2305701, "PRI": 1267427, "PT": 905405, "PVEM": 1128025, "MC": 1234896, "MORENA": 5755609},
    "QUINTA":  {"PAN": 1851623, "PRI": 1724639, "PT": 602275, "PVEM": 896009, "MC": 1195620, "MORENA": 4846725},
}
PRESET_MR = {"PAN": 31, "PRI": 10, "MC": 1, "MORENA": 182, "PVEM": 40, "PT": 34}

# Orden de columnas
PARTIDOS = ["PAN", "PRI", "PT", "PVEM", "MC", "MORENA"]
REGIONES = ["PRIMERA", "SEGUNDA", "TERCERA", "CUARTA", "QUINTA"]

# ---------------------------
# Estado inicial (preset)
# ---------------------------
def _preset_votos_df() -> pd.DataFrame:
    """
    Retorna un DataFrame (index=REGIONES, cols=PARTIDOS) con el preset.
    """
    df = pd.DataFrame(PRESET_VOTOS_REGION).T  # regiones como filas si transponemos?
    # PRESET_VOTOS_REGION es {region: {partido: votos}}
    # DataFrame(PRESET).T deja regiones como filas y partidos como columnas
    # Reordenamos columnas/filas por consistencia:
    df = df.reindex(index=REGIONES, columns=PARTIDOS)
    return df.astype("Int64")

def _preset_mr_df() -> pd.DataFrame:
    return pd.DataFrame({"Partido": list(PRESET_MR.keys()),
                         "Distritos MR": list(PRESET_MR.values())}).astype({"Distritos MR": "Int64"})

if "votos_df" not in st.session_state:
    st.session_state["votos_df"] = _preset_votos_df()
if "mr_df" not in st.session_state:
    st.session_state["mr_df"] = _preset_mr_df()

# ---------------------------
# Controles generales
# ---------------------------
col_top1, col_top2, col_top3 = st.columns([1,1,2])
with col_top1:
    umbral = st.number_input("Umbral nacional mínimo (proporción)", min_value=0.0, max_value=1.0, value=0.03, step=0.01)
with col_top2:
    aplicar_tope = st.checkbox("Aplicar tope de sobrerrepresentación (+8%)", value=True)
with col_top3:
    if st.button("🔄 Restaurar preset"):
        st.session_state["votos_df"] = _preset_votos_df()
        st.session_state["mr_df"] = _preset_mr_df()
        st.success("Preset restaurado.")

st.markdown("### 1) Votos por región (edita en columna)")
st.caption("Rellena/edita los votos por **partido** en cada **región**. Puedes escribir números enteros.")

votos_editados = st.data_editor(
    st.session_state["votos_df"],
    num_rows="fixed",
    use_container_width=True,
    key="votos_editor",
)

# Guardar cambios al estado
st.session_state["votos_df"] = votos_editados

st.markdown("### 2) Distritos de Mayoría Relativa (MR) por partido")
mr_editados = st.data_editor(
    st.session_state["mr_df"],
    num_rows="dynamic",
    use_container_width=True,
    key="mr_editor",
    column_config={
        "Partido": st.column_config.TextColumn(help="Sigla del partido"),
        "Distritos MR": st.column_config.NumberColumn(min_value=0, step=1)
    }
)
st.session_state["mr_df"] = mr_editados

# ---------------------------
# Helpers: transformar a dict
# ---------------------------
def votos_df_a_dict(df: pd.DataFrame) -> dict:
    """
    De un DataFrame (filas=REGIONES, columnas=PARTIDOS) a {region: {partido: votos}}.
    Convierte NaN a 0.
    """
    df_num = df.fillna(0).astype(int)
    out = {}
    for region in df_num.index:
        fila = df_num.loc[region]
        out[region] = {partido: int(fila.get(partido, 0)) for partido in df_num.columns}
    return out

def mr_df_a_dict(df: pd.DataFrame) -> dict:
    """
    De tabla con columnas ['Partido','Distritos MR'] a {partido: int}.
    Ignora filas sin partido o sin número.
    """
    out = {}
    for _, row in df.iterrows():
        p = str(row.get("Partido", "")).strip()
        v = row.get("Distritos MR", None)
        if p and pd.notna(v):
            try:
                out[p] = int(v)
            except Exception:
                pass
    return out

# ---------------------------
# Botón ejecutar
# ---------------------------
st.markdown("---")
if st.button("▶️ Ejecutar asignación"):
    try:
        votos_region = votos_df_a_dict(st.session_state["votos_df"])
        distritos_mr = mr_df_a_dict(st.session_state["mr_df"])

        # VNE nacional = suma por partido en todas las regiones
        # Usamos todas las columnas presentes en el DF (puede haber partidos nuevos)
        partidos_presentes = list(st.session_state["votos_df"].columns)
        vne_nacional = {p: int(st.session_state["votos_df"][p].fillna(0).sum()) for p in partidos_presentes}

        # Construcción de datos y cfg (tus clases ya existen)
        datos = DatosEntrada(votos_region=votos_region,
                             vne_nacional=vne_nacional,
                             distritos_mr=distritos_mr)
        cfg = Config(umbral_nacional=umbral, aplicar_tope_sobrerrep=aplicar_tope)

        # Ejecutar
        resultado = asignar_rp(datos, cfg)

        st.success("Asignación completada.")
        st.subheader("✅ Resultados")

        # Partidos elegibles
        st.write("**Partidos elegibles (>= umbral):**", ", ".join(resultado.elegibles) if resultado.elegibles else "Ninguno")

        # RP nacional por partido
        if getattr(resultado, "rp_nacional_por_partido", None):
            df_rp = pd.DataFrame(
                sorted(resultado.rp_nacional_por_partido.items(), key=lambda x: (-x[1], x[0])),
                columns=["Partido", "Curules RP"]
            )
            st.markdown("**RP nacional por partido**")
            st.dataframe(df_rp, use_container_width=True)

        # Totales MR + RP
        if getattr(resultado, "total_por_partido", None):
            df_tot = pd.DataFrame(
                sorted(resultado.total_por_partido.items(), key=lambda x: (-x[1], x[0])),
                columns=["Partido", "Total Curules"]
            )
            st.markdown("**Totales MR + RP**")
            st.dataframe(df_tot, use_container_width=True)

        # Tope por partido (si aplica)
        if getattr(resultado, "tope_por_partido", None) and resultado.tope_por_partido:
            df_tope = pd.DataFrame(
                sorted(resultado.tope_por_partido.items(), key=lambda x: (-x[1], x[0])),
                columns=["Partido", "Curules después del tope"]
            )
            st.markdown("**Tope de sobrerrepresentación aplicado**")
            st.dataframe(df_tope, use_container_width=True)

        # Asignación por región (muestra tabla región × partido)
        if getattr(resultado, "asignacion_por_region", None):
            # resultado.asignacion_por_region[region].asientos -> dict {partido: curules}
            tabla_regiones = {}
            for region, res in resultado.asignacion_por_region.items():
                tabla_regiones[region] = res.asientos
            # Unir por columnas (partidos) con index=regiones
            df_reg = pd.DataFrame(tabla_regiones).T.fillna(0).astype(int)
            st.markdown("**Asignación por región (curules RP)**")
            st.dataframe(df_reg, use_container_width=True)

        # Notas
        if getattr(resultado, "notas", None):
            if resultado.notas:
                st.info("**Notas:** " + "; ".join([str(n) for n in resultado.notas]))

        # Resumen VNE
        with st.expander("🧮 Ver VNE nacional calculada"):
            df_vne = pd.DataFrame(
                sorted(vne_nacional.items(), key=lambda x: (-x[1], x[0])),
                columns=["Partido", "VNE nacional (votos)"]
            )
            st.dataframe(df_vne, use_container_width=True)

    except Exception as e:
        st.error(f"Error al procesar la asignación: {e}")

# ---------------------------
# Tips de uso
# ---------------------------
with st.expander("ℹ️ Tips"):
    st.write(
        "- Puedes **agregar partidos** en la tabla de MR y en la matriz de votos (añade columna en la matriz y fila en MR). "
        "Asegúrate de que el **nombre coincida** exactamente.\n"
        "- La **VNE nacional** se recalcula automáticamente al ejecutar (suma de votos por partido en todas las regiones)."
    )
