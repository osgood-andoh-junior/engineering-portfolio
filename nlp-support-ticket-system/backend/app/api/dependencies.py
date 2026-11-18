from fastapi import Request


def repository(request: Request):
    return request.app.state.repository


def intelligence(request: Request):
    return request.app.state.intelligence
