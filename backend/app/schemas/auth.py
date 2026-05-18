from pydantic import BaseModel, EmailStr, field_validator


class SignupRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("비밀번호는 8자 이상이어야 합니다.")
        if not any(c.isdigit() for c in v):
            raise ValueError("비밀번호에 숫자가 포함되어야 합니다.")
        if not any(c.isalpha() for c in v):
            raise ValueError("비밀번호에 영문자가 포함되어야 합니다.")
        return v


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
