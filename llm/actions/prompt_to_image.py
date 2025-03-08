"""
@Author: obstacle
@Time: 21/01/25 11:17
@Description:  
"""
import json

from llm.actions.generate_images_by_prompts import generate_image_by_prompt
from constant.base import VA
from utils.common import generate_random_15_digit_number


def prompt_to_image(
        workflow,
        positive_prompt,
        negative_prompt='',
        sampler_name="KSampler",
        seed_name="seed",
        width=512,
        height=768,
        save_previews=False
):
    prompt = json.loads(workflow)
    id_to_class_type = {id: details['class_type'] for id, details in prompt.items()}
    k_sampler = [key for key, value in id_to_class_type.items() if value == sampler_name][0]
    prompt.get(k_sampler)['inputs'][seed_name] = generate_random_15_digit_number()
    latent_id = prompt.get(k_sampler)['inputs']['latent_image'][0]
    prompt.get(latent_id)['inputs']["width"] = width
    prompt.get(latent_id)['inputs']["height"] = height
    positive_input_id = prompt.get(k_sampler)['inputs']['positive'][0]
    prompt.get(positive_input_id)['inputs']['text'] = positive_prompt
    if negative_prompt != '':
        negative_input_id = prompt.get(k_sampler)['inputs']['negative'][0]
        prompt.get(negative_input_id)['inputs']['text'] = negative_prompt
    return generate_image_by_prompt(prompt, str(VA.ROOT_DIR.val / 'data' / 'images'), save_previews)

