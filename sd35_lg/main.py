from io import BytesIO

import torch
from diffusers import (
    BitsAndBytesConfig,
    SD3Transformer2DModel,
    StableDiffusion3Pipeline,
)
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI()

# Load the model and pipeline
model_id = "/data/models/sd35_lg"

nf4_config = BitsAndBytesConfig(
    load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16
)

model_nf4 = SD3Transformer2DModel.from_pretrained(
    model_id,
    subfolder="transformer",
    quantization_config=nf4_config,
    torch_dtype=torch.bfloat16,
)

pipeline = StableDiffusion3Pipeline.from_pretrained(
    model_id, transformer=model_nf4, torch_dtype=torch.bfloat16
)
pipeline.enable_model_cpu_offload()


class ImageGenRequest(BaseModel):

    prompt: str
    num_inference_steps: int = 28
    guidance_scale: float = 4.5
    max_sequence_length: int = 512


@app.post("/generate_image")
async def generate_image(request: ImageGenRequest):
    try:

        prompt = request.prompt
        num_inference_steps = request.num_inference_steps
        guidance_scale = request.guidance_scale
        max_sequence_length = request.max_sequence_length

        # Generate the image
        image = pipeline(
            prompt=prompt,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
            max_sequence_length=max_sequence_length,
        ).images[0]

        # Convert the image to a BytesIO object
        image_bytes = BytesIO()
        image.save(image_bytes, format="PNG")
        image_bytes.seek(0)

        # Return the image as a streaming response
        return StreamingResponse(image_bytes, media_type="image/png")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
