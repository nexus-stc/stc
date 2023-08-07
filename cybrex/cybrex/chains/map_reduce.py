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
    def __init__(self, prompter):
        self.prompter = prompter
        self.chunks = []

    def accept(self, chunk):
        self.chunks.append(chunk)

    def is_full(self):
        return len(self.chunks) >= 7

    def is_empty(self):
        return len(self.chunks) == 0


class QAChunkAccumulator(ChunkAccumulator):
    def __init__(self, query: str, prompter):
        super().__init__(prompter=prompter)
        self.query = query

    def produce(self):
        collected_chunks = self.chunks
        self.chunks = []
        return self.prompter.qa_prompt(self.query, collected_chunks)


class SummarizeChunkAccumulator(ChunkAccumulator):
    def produce(self):
        collected_chunks = self.chunks
        self.chunks = []
        return self.prompter.summarize_prompt(collected_chunks)


class QAChain(MapReduceChain):
    def __init__(self, query: str, llm):
        super().__init__(llm=llm, chunk_accumulator=QAChunkAccumulator(query=query, prompter=llm.prompter))


class SummarizeChain(MapReduceChain):
    def __init__(self, llm):
        super().__init__(llm=llm, chunk_accumulator=SummarizeChunkAccumulator(prompter=llm.prompter))
