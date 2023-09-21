import logging


class LLMManager:
    def __init__(self, llm, prompter, config, max_prompt_chars, tokenizer=None):
        self.llm = llm
        self.prompter = prompter
        self.config = config
        self.max_prompt_chars = max_prompt_chars
        self.tokenizer = tokenizer

    @property
    def context_length(self):
        return self.config['context_length']

    def process(self, prompt):
        logging.getLogger('statbox').info({'action': 'process', 'mode': 'llm_manager', 'prompt': prompt})
        if self.tokenizer:
            input_ids = self.tokenizer(prompt, return_tensors="pt")["input_ids"]
            outputs = self.llm.generate(
                input_ids,
                max_new_tokens=self.config.get('max_new_tokens'),
                temperature=self.config.get('temperature', 1.0),
            )
            return self.tokenizer.batch_decode(outputs[:, input_ids.shape[1]:])[0].replace('</s>', '')
        else:
            return self.llm(prompt)
