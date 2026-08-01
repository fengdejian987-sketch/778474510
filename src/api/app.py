from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.models.seq2seq import FormulaSeq2SeqModel
from src.services.dimension_validator import DimensionValidator

app = FastAPI(title="冯德建公式系统 API", version="2.0")

model = FormulaSeq2SeqModel(model_name='google/mt5-small')
validator = DimensionValidator()

class FormulaRequest(BaseModel):
    description: str
    category: str = None

class FormulaResponse(BaseModel):
    id: str
    name_zh: str
    formula_symbolic: str
    formula_latex: str = None

@app.post('/api/v1/formulas/generate', response_model=FormulaResponse)
def generate_formula(request: FormulaRequest):
    try:
        formula_symbolic = model.generate(request.description)
        validation = validator.validate_formula(formula_symbolic)
        if not validation.get('is_valid'):
            raise HTTPException(status_code=422, detail='量纲不一致')
        return FormulaResponse(id='gen_1', name_zh=request.description, formula_symbolic=formula_symbolic)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
