import cv2
import os


def create_debug_image(
    image_path,
    pv_items,
    output_file
):

    image = cv2.imread(image_path)

    if image is None:
        return

    scale = 3

    for pv in pv_items:

        x = int(pv["x"] * scale)
        y = int(pv["y"] * scale)

        tipo = pv.get("tipo", "")
        codigo = pv.get("codigo", "")

        if tipo == "P":
            color = (0, 0, 255)
        else:
            color = (255, 0, 0)

        cv2.circle(
            image,
            (x, y),
            15,
            color,
            3
        )

        cv2.putText(
            image,
            f"{tipo}-{codigo}",
            (x + 20, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            color,
            2
        )

        if "info" in pv:

            cv2.rectangle(
                image,
                (x + 20, y + 10),
                (x + 250, y + 50),
                color,
                2
            )

            cv2.putText(
                image,
                str(pv["info"]),
                (x + 25, y + 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                color,
                2
            )

    os.makedirs(
        os.path.dirname(output_file),
        exist_ok=True
    )

    cv2.imwrite(
        output_file,
        image
    )