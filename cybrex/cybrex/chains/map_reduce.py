import logging
from typing import List


class MapReduceChain:
    def __init__(self, llm, chunk_accumulator):
        self.llm = llm
        self.chunk_accumulator = chunk_accumulator

    def input_splitter(self, chunks: List) -> str:
        for chunk in chunks:
            self.chunk_accumulator.accept(chunk)
            if self.chunk_accumulator.is_full():
                yield self.chunk_accumulator.produce()
        if not self.chunk_accumulator.is_empty():
            yield self.chunk_accumulator.produce()

    def output_processor(self, llm_output: str) -> dict:
        return {'text': llm_output}

    def process(self, chunks):
        while True:
            input_chunks = self.input_splitter(chunks)
            outputs = []
            for input_chunk in input_chunks:
                llm_output = self.llm.process(input_chunk)
                logging.getLogger('statbox').info({
                    'action': 'intermediate_map_reduce_step',
                    'output': llm_output,
                })
                outputs.append(llm_output)
            if len(outputs) == 1:
                return outputs[0].strip()
            chunks = list(map(self.output_processor, outputs))


class ChunkAccumulator:
    def __init__(self, prompter, max_chunk_length: int):
        self.prompter = prompter
        self.max_chunk_length = max_chunk_length
        self.chunks = []
        self.current_chunk_length = 0

    def accept(self, chunk):
        self.current_chunk_length += len(chunk['text'])
        self.chunks.append(chunk)

    def is_full(self):
        return self.current_chunk_length >= self.max_chunk_length

    def is_empty(self):
        return len(self.chunks) == 0


class QAChunkAccumulator(ChunkAccumulator):
    def __init__(self, query: str, prompter, max_chunk_length: int):
        super().__init__(prompter=prompter, max_chunk_length=max_chunk_length)
        self.query = query

    def produce(self):
        collected_chunks = self.chunks
        self.chunks = []
        self.current_chunk_length = 0
        return self.prompter.qa_prompt(self.query, collected_chunks)


class SummarizeChunkAccumulator(ChunkAccumulator):
    def produce(self):
        collected_chunks = self.chunks
        self.chunks = []
        self.current_chunk_length = 0
        return self.prompter.summarize_prompt(collected_chunks)


class QAChain(MapReduceChain):
    def __init__(self, query: str, llm):
        super().__init__(
            llm=llm,
            chunk_accumulator=QAChunkAccumulator(
                query=query,
                prompter=llm.prompter,
                max_chunk_length=llm.max_prompt_chars,
            ))


class SummarizeChain(MapReduceChain):
    def __init__(self, llm):
        super().__init__(
            llm=llm,
            chunk_accumulator=SummarizeChunkAccumulator(
                prompter=llm.prompter,
                max_chunk_length=llm.max_prompt_chars,
            )
        )
