import cv2
import numpy as np


class ArrowDetector:
    """
    Detecta linhas/setas em plantas eletricas.

    Melhorias em relacao a versao anterior:
    - Pre-processamento morfologico: fecha gaps das linhas tracejadas antes
      do Canny, unindo segmentos quebrados em uma linha continua.
    - HoughLinesP com maxLineGap maior (30 px) para unir tracejados.
    - Encadeamento de segmentos colineares: une segmentos que apontam
      para a mesma direcao e ficam proximos, reconstruindo setas longas
      que foram partidas em varios pedacos.
    - find_nearest_line agora busca tanto nas extremidades quanto no
      ponto medio da linha, pegando setas que passam "por cima" do rotulo.
    """

    # Parametros de deteccao - ajuste aqui se necessario
    CANNY_LOW        = 40    # limiar inferior Canny (menor = mais bordas)
    CANNY_HIGH       = 120   # limiar superior Canny
    HOUGH_THRESHOLD  = 40    # votos minimos para aceitar linha
    HOUGH_MIN_LEN    = 15    # comprimento minimo de segmento (px)
    HOUGH_MAX_GAP    = 30    # gap maximo para unir segmentos (tracejado)
    MERGE_DISTANCE   = 18    # distancia maxima para encadear segmentos
    MERGE_ANGLE_DEG  = 15    # diferenca angular maxima para encadear

    def __init__(self, image_path: str):
        self.image = cv2.imread(image_path)
        if self.image is None:
            raise FileNotFoundError(f"Imagem nao encontrada: {image_path}")
        self.gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        self._lines: list[dict] | None = None

    # ── Cache de linhas ───────────────────────────────────────────────────────

    @property
    def lines(self) -> list[dict]:
        if self._lines is None:
            self._lines = self._detect_lines()
        return self._lines

    def _preprocess(self) -> np.ndarray:
        """
        Pre-processa a imagem para fechar gaps de linhas tracejadas.
        Kernel horizontal + vertical fecha pequenos buracos antes do Canny.
        """
        # Binariza
        _, binary = cv2.threshold(self.gray, 200, 255, cv2.THRESH_BINARY_INV)

        # Fecha gaps com dilatacao leve (une tracejados)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 1))
        closed_h = cv2.dilate(binary, kernel, iterations=1)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 5))
        closed_v = cv2.dilate(binary, kernel, iterations=1)
        closed = cv2.bitwise_or(closed_h, closed_v)

        # Canny sobre imagem pre-processada
        edges = cv2.Canny(closed, self.CANNY_LOW, self.CANNY_HIGH)
        return edges

    def _detect_lines(self) -> list[dict]:
        edges = self._preprocess()

        raw = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=self.HOUGH_THRESHOLD,
        minLineLength=self.HOUGH_MIN_LEN,
        maxLineGap=self.HOUGH_MAX_GAP,
        )

        if raw is None:
            return []

        segments = [
            {"x1": int(x1), "y1": int(y1), "x2": int(x2), "y2": int(y2)}
            for x1, y1, x2, y2 in raw[:, 0]
        ]

        print("SEGMENTOS ENCONTRADOS:", len(segments))

    # TESTE TEMPORÁRIO
        return segments

    # ── Encadeamento de segmentos colineares ──────────────────────────────────

    @staticmethod
    def _angle(seg: dict) -> float:
        """Angulo do segmento em graus [-90, 90]."""
        dx = seg["x2"] - seg["x1"]
        dy = seg["y2"] - seg["y1"]
        return np.degrees(np.arctan2(dy, dx)) % 180

    def _merge_segments(self, segments: list[dict]) -> list[dict]:
        """
        Une segmentos que estao proximos E apontam na mesma direcao.
        Resultado: menos fragmentos, setas mais longas e mais faceis de seguir.
        """
        merged = list(segments)
        changed = True
        while changed:
            changed = False
            used = [False] * len(merged)
            result = []
            for i, a in enumerate(merged):
                if used[i]:
                    continue
                best_j = None
                best_d = float("inf")
                for j, b in enumerate(merged):
                    if i == j or used[j]:
                        continue
                    # Diferenca angular
                    da = abs(self._angle(a) - self._angle(b))
                    da = min(da, 180 - da)
                    if da > self.MERGE_ANGLE_DEG:
                        continue
                    # Distancia entre extremidades
                    d = min(
                        np.hypot(a["x2"] - b["x1"], a["y2"] - b["y1"]),
                        np.hypot(a["x2"] - b["x2"], a["y2"] - b["y2"]),
                        np.hypot(a["x1"] - b["x1"], a["y1"] - b["y1"]),
                        np.hypot(a["x1"] - b["x2"], a["y1"] - b["y2"]),
                    )
                    if d < self.MERGE_DISTANCE and d < best_d:
                        best_d = d
                        best_j = j
                if best_j is not None:
                    b = merged[best_j]
                    # Junta os dois: pega o bounding box das 4 extremidades
                    xs = [a["x1"], a["x2"], b["x1"], b["x2"]]
                    ys = [a["y1"], a["y2"], b["y1"], b["y2"]]
                    # Escolhe as duas extremidades mais distantes entre si
                    pts = list(zip(xs, ys))
                    max_d = 0
                    p1, p2 = pts[0], pts[1]
                    for pi in pts:
                        for pj in pts:
                            d = np.hypot(pi[0] - pj[0], pi[1] - pj[1])
                            if d > max_d:
                                max_d = d
                                p1, p2 = pi, pj
                    result.append({"x1": p1[0], "y1": p1[1], "x2": p2[0], "y2": p2[1]})
                    used[i] = True
                    used[best_j] = True
                    changed = True
                else:
                    result.append(a)
                    used[i] = True
            merged = result
        return merged

    # ── API publica ───────────────────────────────────────────────────────────

    def draw_lines(self, output_file: str) -> None:
        image = self.image.copy()
        for line in self.lines:
            cv2.line(
                image,
                (line["x1"], line["y1"]),
                (line["x2"], line["y2"]),
                (0, 255, 0),
                1,
            )
        cv2.imwrite(output_file, image)

    def find_nearest_line(
        self,
        target_x: float,
        target_y: float,
        max_distance: float = 80,
    ) -> dict | None:
        """
        Busca a linha mais proxima ao ponto (target_x, target_y).
        Verifica extremidades E ponto medio — pega setas que passam
        por cima do rotulo P/V, nao so as que comecam nele.
        """
        best_line = None
        best_dist = float("inf")

        for line in self.lines:
            mx = (line["x1"] + line["x2"]) / 2
            my = (line["y1"] + line["y2"]) / 2
            d = min(
                np.hypot(line["x1"] - target_x, line["y1"] - target_y),
                np.hypot(line["x2"] - target_x, line["y2"] - target_y),
                np.hypot(mx - target_x, my - target_y),
            )
            if d < best_dist and d <= max_distance:
                best_dist = d
                best_line = line

        return best_line

    def line_destination(
        self,
        line: dict,
        origin_x: float,
        origin_y: float,
    ) -> tuple[float, float] | None:
        if line is None:
            return None
        d1 = np.hypot(line["x1"] - origin_x, line["y1"] - origin_y)
        d2 = np.hypot(line["x2"] - origin_x, line["y2"] - origin_y)
        if d1 < d2:
            return line["x2"], line["y2"]
        return line["x1"], line["y1"]
