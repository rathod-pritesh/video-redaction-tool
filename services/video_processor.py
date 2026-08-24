import cv2
from ultralytics import YOLO


MODEL_PATH = "yolo26n.pt"

CONFIDENCE = 0.50
IOU_THRESHOLD = 0.50
IMAGE_SIZE = 512

MAX_MISSING_FRAMES = 5

REDACT_CLASS_IDS = {
    0,  # person
    2,  # car
    3,  # motorcycle
    5,  # bus
}

model = YOLO(MODEL_PATH)

def blur_region(frame, x1, y1, x2, y2):
    region = frame[y1:y2, x1:x2]

    if region.size == 0:
        return

    blurred = cv2.GaussianBlur(
        region,
        (51, 51),
        0
    )

    frame[y1:y2, x1:x2] = blurred


def add_padding(x1, y1, x2, y2, width, height):
    box_width = x2 - x1
    box_height = y2 - y1

    padding_x = int(box_width * 0.10)
    padding_y = int(box_height * 0.15)

    x1 -= padding_x
    y1 -= padding_y
    x2 += padding_x
    y2 += padding_y

    return (
        max(0, x1),
        max(0, y1),
        min(width, x2),
        min(height, y2),
    )


def boxes_are_rider_and_motorcycle(person_box, motorcycle_box):
    px1, py1, px2, py2 = person_box
    mx1, my1, mx2, my2 = motorcycle_box

    person_width = px2 - px1
    motorcycle_width = mx2 - mx1
    motorcycle_height = my2 - my1

    if person_width <= 0 or motorcycle_width <= 0:
        return False

    overlap_x1 = max(px1, mx1)
    overlap_x2 = min(px2, mx2)

    overlap_width = max(0, overlap_x2 - overlap_x1)

    horizontal_overlap = overlap_width / min(
        person_width,
        motorcycle_width
    )

    if horizontal_overlap < 0.20:
        return False

    vertical_gap = max(0, my1 - py2)

    max_vertical_gap = motorcycle_height * 0.35

    return vertical_gap <= max_vertical_gap


def merge_boxes(box1, box2, width, height):
    x1 = min(box1[0], box2[0])
    y1 = min(box1[1], box2[1])
    x2 = max(box1[2], box2[2])
    y2 = max(box1[3], box2[3])

    return add_padding(
        x1,
        y1,
        x2,
        y2,
        width,
        height
    )


def process_video(input_path, output_path):

    cap = cv2.VideoCapture(input_path)

    if not cap.isOpened():
        raise ValueError("Unable to open video")

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if fps <= 0 or width <= 0 or height <= 0:
        cap.release()
        raise ValueError("Invalid video properties")

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")

    writer = cv2.VideoWriter(
        output_path,
        fourcc,
        fps,
        (width, height)
    )

    if not writer.isOpened():
        cap.release()
        raise ValueError("Unable to create output video")

    active_tracks = {}

    try:

        while True:

            success, frame = cap.read()

            if not success:
                break

            results = model.track(
                frame,
                persist=True,
                tracker="bytetrack.yaml",
                imgsz=IMAGE_SIZE,
                conf=CONFIDENCE,
                iou=IOU_THRESHOLD,
                classes=list(REDACT_CLASS_IDS),
                verbose=False
            )

            current_tracks = {}
            detected_boxes = []

            for result in results:

                if result.boxes is None:
                    continue

                boxes = result.boxes

                for index in range(len(boxes)):

                    class_id = int(boxes.cls[index])

                    if class_id not in REDACT_CLASS_IDS:
                        continue

                    confidence = float(boxes.conf[index])

                    if confidence < CONFIDENCE:
                        continue

                    x1, y1, x2, y2 = map(
                        int,
                        boxes.xyxy[index]
                    )

                    x1 = max(0, x1)
                    y1 = max(0, y1)
                    x2 = min(width, x2)
                    y2 = min(height, y2)

                    box = (x1, y1, x2, y2)

                    detected_boxes.append(
                        (class_id, box, confidence)
                    )

                    if boxes.id is not None:

                        tracker_id = int(boxes.id[index])

                        center_x = (x1 + x2) // 2
                        center_y = (y1 + y2) // 2

                        previous = active_tracks.get(tracker_id)

                        velocity_x = 0
                        velocity_y = 0

                        if previous is not None:

                            previous_box = previous["box"]

                            previous_center_x = (
                                previous_box[0] +
                                previous_box[2]
                            ) // 2

                            previous_center_y = (
                                previous_box[1] +
                                previous_box[3]
                            ) // 2

                            velocity_x = (
                                center_x -
                                previous_center_x
                            )

                            velocity_y = (
                                center_y -
                                previous_center_y
                            )

                        current_tracks[tracker_id] = {
                            "class_id": class_id,
                            "box": box,
                            "velocity_x": velocity_x,
                            "velocity_y": velocity_y,
                            "missing": 0,
                        }

            for tracker_id, track in active_tracks.items():

                if tracker_id in current_tracks:
                    continue

                missing = track["missing"] + 1

                if missing > MAX_MISSING_FRAMES:
                    continue

                x1, y1, x2, y2 = track["box"]

                velocity_x = track["velocity_x"]
                velocity_y = track["velocity_y"]

                x1 += velocity_x
                y1 += velocity_y
                x2 += velocity_x
                y2 += velocity_y

                predicted_box = (
                    max(0, x1),
                    max(0, y1),
                    min(width, x2),
                    min(height, y2),
                )

                current_tracks[tracker_id] = {
                    "class_id": track["class_id"],
                    "box": predicted_box,
                    "velocity_x": velocity_x,
                    "velocity_y": velocity_y,
                    "missing": missing,
                }

                detected_boxes.append(
                    (
                        track["class_id"],
                        predicted_box,
                        None
                    )
                )

            active_tracks = current_tracks

            person_boxes = []
            motorcycle_boxes = []
            other_boxes = []

            for class_id, box, confidence in detected_boxes:

                if class_id == 0:
                    person_boxes.append((box, confidence))

                elif class_id == 3:
                    motorcycle_boxes.append((box, confidence))

                else:
                    other_boxes.append((class_id, box, confidence))

            combined_rider_boxes = []

            matched_persons = set()
            matched_motorcycles = set()

            for person_index, person_box in enumerate(person_boxes):

                for motorcycle_index, motorcycle_box in enumerate(
                    motorcycle_boxes
                ):

                    if boxes_are_rider_and_motorcycle(
                        person_box,
                        motorcycle_box
                    ):

                        combined_box = merge_boxes(
                            person_box,
                            motorcycle_box,
                            width,
                            height
                        )

                        combined_rider_boxes.append(
                            combined_box
                        )

                        matched_persons.add(person_index)
                        matched_motorcycles.add(motorcycle_index)

            for box in combined_rider_boxes:

                blur_region(
                    frame,
                    *box
                )
                
                cv2.rectangle(
                    frame,
                    (box[0], box[1]),
                    (box[2], box[3]),
                    (61, 90, 201),
                    2,
                )

            for index, (box, confidence) in enumerate(person_boxes):

                if index in matched_persons:
                    continue

                padded_box = add_padding(
                    *box,
                    width,
                    height
                )

                blur_region(
                    frame,
                    *padded_box
                )
                
                cv2.rectangle(
                    frame,
                    (padded_box[0], padded_box[1]),
                    (padded_box[2], padded_box[3]),
                    (61, 90, 201),
                    2,
                )
                
                if confidence is not None:
                    label = f"Person {confidence * 100:.0f}%"
                    
                    cv2.putText(
                        frame,
                        label,
                        (padded_box[0], max(25, padded_box[1] -8)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (61, 90, 201),
                        2,
                        cv2.LINE_AA
                    )

            for index, (box, confidence) in enumerate(motorcycle_boxes):

                if index in matched_motorcycles:
                    continue

                padded_box = add_padding(
                    *box,
                    width,
                    height
                )

                blur_region(
                    frame,
                    *padded_box
                )
                
                cv2.rectangle(
                    frame,
                    (padded_box[0], padded_box[1]),
                    (padded_box[2], padded_box[3]),
                    (61, 90, 201),
                    2,
                )
                
                if confidence is not None:
                    label = f"Motorcycle {confidence * 100:.0f}%"
                    
                    cv2.putText(
                        frame,
                        label,
                        (padded_box[0], max(25, padded_box[1] - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (61, 90, 201),
                        2,
                        cv2.LINE_AA
                    )

            for class_id, box, confidence in other_boxes:

                padded_box = add_padding(
                    *box,
                    width,
                    height
                )

                blur_region(
                    frame,
                    *padded_box
                )
                
                cv2.rectangle(
                    frame,
                    (padded_box[0], padded_box[1]),
                    (padded_box[2], padded_box[3]),
                    (61, 90, 201),
                    2,
                )
                
                if confidence is not None:
                    class_name = model.names[class_id]
                    label = f"{class_name.title()} {confidence * 100:.0f}%"
                    
                    cv2.putText(
                        frame,
                        label,
                        (padded_box[0], max(25, padded_box[1] - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (61, 90, 201),
                        2,
                        cv2.LINE_AA
                    )

            writer.write(frame)

    finally:

        cap.release()
        writer.release()