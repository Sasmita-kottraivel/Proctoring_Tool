from flask import Flask, request, jsonify
from flask_cors import CORS

import torch
import torch.nn as nn

from torchvision import models, transforms
from PIL import Image

import io


# =========================================================
# CONFIGURATION
# =========================================================

MODEL_PATH = r"C:\Users\dharu\BottleDetection\best_model.pt"

CONFIDENCE_THRESHOLD = 0.60

DEVICE = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


# =========================================================
# FLASK APPLICATION
# =========================================================

app = Flask(__name__)
CORS(app)


# =========================================================
# LOAD MODEL
# =========================================================

def load_model(model_path):

    print()
    print("Loading model...")
    print("Model path:", model_path)

    checkpoint = torch.load(
        model_path,
        map_location=DEVICE
    )

    # Get information saved inside the checkpoint
    class_names = checkpoint["class_names"]
    img_size = checkpoint["img_size"]

    # Create ResNet18
    model = models.resnet18(weights=None)

    # Replace final layer
    model.fc = nn.Linear(
        model.fc.in_features,
        len(class_names)
    )

    # Load trained weights
    model.load_state_dict(
        checkpoint["model_state_dict"]
    )

    # Move model to CPU/GPU
    model.to(DEVICE)

    # Evaluation mode
    model.eval()

    # Same preprocessing used during training
    transform = transforms.Compose([

        transforms.Resize(
            int(img_size * 1.14)
        ),

        transforms.CenterCrop(
            img_size
        ),

        transforms.ToTensor(),

        transforms.Normalize(
            IMAGENET_MEAN,
            IMAGENET_STD
        )
    ])

    print()
    print("====================================")
    print("MODEL LOADED SUCCESSFULLY")
    print("====================================")

    print("Classes:", class_names)
    print("Image size:", img_size)
    print("Device:", DEVICE)

    print("====================================")
    print()

    return model, class_names, transform


# Load model once when server starts
model, class_names, transform = load_model(
    MODEL_PATH
)


# =========================================================
# IMAGE PREDICTION
# =========================================================

def predict_image(image):

    # Make sure image is RGB
    image = image.convert("RGB")

    # Apply preprocessing
    tensor = transform(image)

    # Add batch dimension
    tensor = tensor.unsqueeze(0)

    # Move to CPU/GPU
    tensor = tensor.to(DEVICE)

    # Disable gradient calculation
    with torch.no_grad():

        outputs = model(tensor)

        # Convert model output to probabilities
        probabilities = torch.softmax(
            outputs,
            dim=1
        )[0]

        # Find highest probability
        pred_idx = probabilities.argmax().item()

        predicted_class = class_names[pred_idx]

        confidence = probabilities[
            pred_idx
        ].item()

    # All class probabilities
    all_probabilities = {

        class_names[i]:
            round(
                probabilities[i].item(),
                4
            )

        for i in range(
            len(class_names)
        )
    }

    return {

        "predicted_class":
            predicted_class,

        "confidence":
            round(confidence, 4),

        "all_probabilities":
            all_probabilities
    }


# =========================================================
# HOME / STATUS ROUTE
# =========================================================

@app.route("/", methods=["GET"])
def home():

    return jsonify({

        "status":
            "Bottle AI Server Running",

        "classes":
            class_names,

        "confidence_threshold":
            CONFIDENCE_THRESHOLD,

        "device":
            str(DEVICE)
    })


# =========================================================
# PREDICT ROUTE
#
# ESP32-CAM sends:
# Content-Type: image/jpeg
#
# The JPEG is received directly as raw data.
# =========================================================

@app.route("/predict", methods=["POST"])
def predict():

    try:

        print()
        print("====================================")
        print("NEW IMAGE REQUEST")
        print("====================================")


        # -------------------------------------------------
        # RECEIVE RAW JPEG
        # -------------------------------------------------

        image_bytes = request.get_data()

        print(
            "Bytes received:",
            len(image_bytes)
        )


        # Check if data exists
        if not image_bytes:

            print(
                "ERROR: No image data received"
            )

            return jsonify({

                "success": False,

                "error":
                    "No image data received"

            }), 400


        # -------------------------------------------------
        # OPEN JPEG IMAGE
        # -------------------------------------------------

        try:

            image = Image.open(
                io.BytesIO(image_bytes)
            )

            image.load()

        except Exception as image_error:

            print(
                "ERROR: Invalid image"
            )

            print(
                image_error
            )

            return jsonify({

                "success": False,

                "error":
                    "Invalid JPEG image"

            }), 400


        print(
            "Image size:",
            image.size
        )

        print(
            "Image format:",
            image.format
        )


        # -------------------------------------------------
        # RUN MODEL
        # -------------------------------------------------

        result = predict_image(
            image
        )


        predicted_class = (
            result["predicted_class"]
        )

        confidence = (
            result["confidence"]
        )


        # -------------------------------------------------
        # CONFIDENCE CHECK
        # -------------------------------------------------

        if confidence < CONFIDENCE_THRESHOLD:

            action = "REJECT"

            material = "UNKNOWN"


        else:

            # ---------------------------------------------
            # CLASSIFICATION
            # ---------------------------------------------

            if predicted_class == "PET":

                material = "PLASTIC"
                action = "TRIGGER_SERVO"


            elif predicted_class == "HDPEM":

                material = "PLASTIC"
                action = "TRIGGER_SERVO"


            elif predicted_class == "Glass":

                material = "GLASS"
                action = "TRIGGER_SERVO"


            elif predicted_class == "AluCan":

                material = "ALUMINIUM"
                action = "TRIGGER_SERVO"


            else:

                material = "UNKNOWN"
                action = "REJECT"


        # -------------------------------------------------
        # PRINT RESULT
        # -------------------------------------------------

        print()
        print("------------------------------------")

        print(
            "Predicted class:",
            predicted_class
        )

        print(
            "Confidence:",
            confidence
        )

        print(
            "Material:",
            material
        )

        print(
            "Action:",
            action
        )

        print(
            "All probabilities:",
            result["all_probabilities"]
        )

        print("------------------------------------")


        # -------------------------------------------------
        # SEND JSON RESPONSE TO ESP32-CAM
        # -------------------------------------------------

        response = {

            "success":
                True,

            "predicted_class":
                predicted_class,

            "confidence":
                confidence,

            "material":
                material,

            "action":
                action,

            "all_probabilities":
                result[
                    "all_probabilities"
                ]
        }


        print(
            "Sending response to ESP32-CAM..."
        )

        print(
            response
        )

        print(
            "===================================="
        )


        return jsonify(response)


    # =====================================================
    # ERROR HANDLING
    # =====================================================

    except Exception as e:

        print()
        print("====================================")
        print("PREDICTION ERROR")
        print("====================================")

        print(
            type(e).__name__
        )

        print(
            str(e)
        )

        print(
            "===================================="
        )


        return jsonify({

            "success":
                False,

            "error":
                str(e)

        }), 500


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":

    print()
    print("====================================")
    print("   BOTTLE AI CLASSIFICATION SERVER")
    print("====================================")

    print()
    print("Server starting...")
    print()
    print("Laptop IP: 10.193.89.12")
    print("Port: 5000")
    print()
    print("AI endpoint:")
    print("http://10.193.89.12:5000/predict")
    print()
    print("Classes:")
    print(class_names)
    print()
    print("Confidence threshold:")
    print(CONFIDENCE_THRESHOLD)
    print()
    print("====================================")
    print()


    app.run(

        host="0.0.0.0",

        port=5000,

        debug=False
    )
