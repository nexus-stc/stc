import os.path
from typing import Dict

import fasttext

if os.path.exists('./library/sciparse/models/lid.176.bin'):
    path_to_pretrained_model = './library/sciparse/models/lid.176.bin'
    fmodel = fasttext.load_model(path_to_pretrained_model)
else:
    path_to_pretrained_model = './library/sciparse/models/lid.176.ftz'
    fmodel = fasttext.load_model(path_to_pretrained_model)


def detect_language(text: str, threshold: float = 0.85) -> Dict[str, float]:
    prediction = fmodel.predict([text.replace('\n', ' ')], threshold=threshold)
    if prediction[0][0]:
        return prediction[0][0][0][-2:]
