from src.modules.auth.utils.hash_generation import pw_manager


def test_hash_and_check_roundtrip():
    hashed = pw_manager.hash_password("som@Th1ng")
    assert pw_manager.check_password("som@Th1ng", hashed) is True


def test_check_wrong_password_returns_false():
    hashed = pw_manager.hash_password("som@Th1ng")
    assert pw_manager.check_password("different", hashed) is False


def test_hash_is_bytes():
    hashed = pw_manager.hash_password("som@Th1ng")
    assert isinstance(hashed, bytes)


def test_same_password_hashes_differ():
    first = pw_manager.hash_password("som@Th1ng")
    second = pw_manager.hash_password("som@Th1ng")
    assert first != second


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("hash generation tests passed")