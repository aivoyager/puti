"""
@Author: obstacle
@Time: 21/01/25 11:35
@Description:  
"""

from logs import logger_factory
from constant.base import VA
from utils.common import load_workflow
from llm.actions.prompt_to_image import prompt_to_image

lgr = logger_factory.default


class ComfyUIClient:

    def generate_sheldon(self, width=512, height=768) -> str:
        workflow_path = str(VA.ROOT_DIR.val.parent / 'conf' / 'workflows' / 'sheldon.json')
        workflow = load_workflow(workflow_path)
        positive = 'Sheldon Cooper,thin and weak,red clothes (sharp focus:1.1) (detailed cloth:1.1),(masterpiece), (best quality:1.3),8k,HDR,wallpaper,cinematic lighting,,glowing, eyes,santa, santa claus, white hair, red pants, santa hat, mustache BREAK CoralVG, happy smile,(realistic:1.3),open mout'
        negative = '(illustration, 3d, sepia:1.1), (deformed, distorted, disfigured:1.1), poorly drawn, bad anatomy, wrong anatomy, extra limb, missing limb, floating limbs, (mutated hands and fingers:1.1), disconnected limbs, mutation, mutated, ugly, disgusting, blurry, amputation,'
        path = prompt_to_image(workflow, positive_prompt=positive, negative_prompt=negative, width=width, height=height,
                               sampler_name="KSamplerAdvanced", seed_name="noise_seed", save_previews=True)
        if path:
            lgr.info('comfyui generate image success')
            return path


comfyui_client = ComfyUIClient()
