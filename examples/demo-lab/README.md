# Demo Authorization Review

## 1. Informações gerais

- Plataforma: Local Demo
- Categoria: Access Control
- Dificuldade: Beginner
- Link original: <https://example.invalid/labs/authorization-review>

## 2. Objetivo

Document a fictional authorization check using only synthetic requests and responses.

## 3. Metodologia geral

The demo compares an authorized request with a deliberately fictional denied request. No real service, credential, account, or vulnerability is represented.

## 4. Vulnerabilidade

### Missing object ownership check

- Categoria: Access Control
- CWE: CWE-639
- Status: confirmed

#### Descrição

The fictional endpoint accepts an object identifier. The example demonstrates how an ownership check should be documented.

#### Passos de reprodução

1. Send the synthetic request in `evidence/evidence-01.http`.
2. Observe the synthetic denied response in `evidence/evidence-02.txt`.
3. Record the expected authorization behavior.

#### Evidências

### 01 · Authorization request

[Synthetic HTTP request](evidence/evidence-01.http)

_Synthetic HTTP request_

### 02 · Expected result

[Synthetic denied response](evidence/evidence-02.txt)

_Synthetic denied response_

#### Impacto

In a real application, a missing ownership check could expose another user's object. This demo does not target a real application.

#### Mitigação

Enforce object-level authorization on the server for every request and test allowed and denied cases.

## 5. Conclusão e aprendizados

Clear reproduction steps, sanitized evidence, and an explicit expected result make an authorization report easier to review safely.
