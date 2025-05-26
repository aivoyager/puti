"""
@Author: obstacles
@Time:  2025-04-17 15:43
@Description:  
"""
import os

from google import genai
from google.genai import types
from puti.conf.client_config import GoogleConfig

gc = GoogleConfig()

os.environ['GOOGLE_API_KEY'] = gc.GOOGLE_API_KEY


def test_finetune_gemini_by_api():
    client = genai.Client()  # Get the key from the GOOGLE_API_KEY env variable

    for model_info in client.models.list():
        print(model_info.name)
    training_dataset = [
        ["1", "2"],
        ["3", "4"],
        ["-3", "-2"],
        ["twenty two", "twenty three"],
        ["two hundred", "two hundred one"],
        ["ninety nine", "one hundred"],
        ["8", "9"],
        ["-98", "-97"],
        ["1,000", "1,001"],
        ["10,100,000", "10,100,001"],
        ["thirteen", "fourteen"],
        ["eighty", "eighty one"],
        ["one", "two"],
        ["three", "four"],
        ["seven", "eight"],
    ]
    training_dataset = types.TuningDataset(
        examples=[
            types.TuningExample(
                text_input=i,
                output=o,
            )
            for i, o in training_dataset
        ],
    )
    tuning_job = client.tunings.tune(
        base_model='models/gemini-1.5-flash-001-tuning',
        training_dataset=training_dataset,
        config=types.CreateTuningJobConfig(
            epoch_count=5,
            batch_size=4,
            learning_rate=0.001,
            tuned_model_display_name="test tuned model"
        )
    )

    print('')
