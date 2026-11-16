def _generate_stats_values(method: str) -> dict:
    from src.modules.character.draft import service

    if method == "standard":
        generated = service.generate_standard_array()
    elif method == "point_buy":
        generated = service.generate_point_buy_stats()
    elif method == "random":
        generated = service.generate_random_stats()
    else:
        raise service.ServiceError(
            msg=f"Unsupported stats generation method: {method}.", code=422
        )
    return service.assign_stats(generated)
