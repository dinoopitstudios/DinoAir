"""
Unit tests for artifact_encryption.py module.
Tests encryption/decryption functionality and field-level operations.
"""

import pytest

from ..artifact_encryption import ArtifactEncryption, decrypt_text, encrypt_text


class TestArtifactEncryption:
    """Test cases for ArtifactEncryption class."""

    def test_initialization_with_password(self):
        """Test initialization with password."""
        password = "test_password"
        encryptor = ArtifactEncryption(password)

        if encryptor.password != password:
            raise AssertionError

    def test_initialization_without_password(self):
        """Test initialization without password."""
        encryptor = ArtifactEncryption()

        assert encryptor.password is None

    def test_derive_key(self):
        """Test key derivation from password and salt."""
        password = "test_password"
        salt = b"test_salt_32_bytes_long_salt!!"

        encryptor = ArtifactEncryption(password)
        key = encryptor.derive_key(password, salt)

        assert len(key) == 32  # AES-256 key length
        assert isinstance(key, bytes)

    def test_generate_salt(self):
        """Test salt generation."""
        encryptor = ArtifactEncryption()
        salt = encryptor.generate_salt()

        assert len(salt) == 32
        assert isinstance(salt, bytes)

    def test_generate_iv(self):
        """Test IV generation."""
        encryptor = ArtifactEncryption()
        iv = encryptor.generate_iv()

        assert len(iv) == 16  # AES block size
        assert isinstance(iv, bytes)

    def test_encrypt_decrypt_data_string(self):
        """Test encrypting and decrypting string data."""
        password = "test_password"
        data = "Hello, World!"

        encryptor = ArtifactEncryption(password)

        # Encrypt
        encrypted = encryptor.encrypt_data(data)
        assert isinstance(encrypted, dict)
        if "data" not in encrypted:
            raise AssertionError
        if "salt" not in encrypted:
            raise AssertionError
        if "iv" not in encrypted:
            raise AssertionError

        # Decrypt
        decrypted = encryptor.decrypt_data(encrypted)
        if decrypted.decode("utf-8") != data:
            raise AssertionError

    def test_encrypt_decrypt_data_bytes(self):
        """Test encrypting and decrypting bytes data."""
        password = "test_password"
        data = b"Hello, World!"

        encryptor = ArtifactEncryption(password)

        # Encrypt
        encrypted = encryptor.encrypt_data(data)

        # Decrypt
        decrypted = encryptor.decrypt_data(encrypted)
        if decrypted != data:
            raise AssertionError

    def test_encrypt_data_invalid_type(self):
        """Test encrypting invalid data type."""
        encryptor = ArtifactEncryption("password")

        with pytest.raises(TypeError):
            encryptor.encrypt_data(123)  # Invalid type

    def test_encrypt_without_password_no_key(self):
        """Test encryption without password and no key provided."""
        encryptor = ArtifactEncryption()  # No password

        with pytest.raises(ValueError, match="No password provided"):
            encryptor.encrypt_data("test")

    def test_decrypt_without_password_no_key(self):
        """Test decryption without password and no key provided."""
        encryptor = ArtifactEncryption()  # No password

        encrypted_data = {
            "data": "fake_encrypted",
            "salt": "fake_salt",
            "iv": "fake_iv",
        }

        with pytest.raises(ValueError, match="No password provided"):
            encryptor.decrypt_data(encrypted_data)

    def test_encrypt_decrypt_with_provided_key(self):
        """Test encryption/decryption with explicitly provided key."""
        password = "test_password"
        data = "Test data"

        encryptor = ArtifactEncryption(password)

        # Generate key
        salt = encryptor.generate_salt()
        key = encryptor.derive_key(password, salt)

        # Encrypt with key
        encrypted = encryptor.encrypt_data(data, key)

        # Decrypt with key
        decrypted = encryptor.decrypt_data(encrypted, key)
        if decrypted.decode("utf-8") != data:
            raise AssertionError

    def test_encrypt_fields(self):
        """Test encrypting specific fields in a dictionary."""
        password = "test_password"
        data = {
            "id": "123",
            "name": "John Doe",
            "email": "john@example.com",
            "public_info": "This is public",
        }
        fields_to_encrypt = ["name", "email"]

        encryptor = ArtifactEncryption(password)
        encrypted_data = encryptor.encrypt_fields(data, fields_to_encrypt)

        # Check that specified fields are encrypted
        if encrypted_data["name"] == "John Doe":
            raise AssertionError
        if encrypted_data["email"] == "john@example.com":
            raise AssertionError
        if encrypted_data["id"] != "123":
            raise AssertionError
        if encrypted_data["public_info"] != "This is public":
            raise AssertionError

        # Check encryption metadata
        if "_encryption_info" not in encrypted_data:
            raise AssertionError
        if "name" not in encrypted_data["_encryption_info"]:
            raise AssertionError
        if "email" not in encrypted_data["_encryption_info"]:
            raise AssertionError

    def test_decrypt_fields(self):
        """Test decrypting specific fields in a dictionary."""
        password = "test_password"
        original_data = {"id": "123", "name": "John Doe", "email": "john@example.com"}

        encryptor = ArtifactEncryption(password)
        encrypted_data = encryptor.encrypt_fields(original_data, ["name", "email"])

        # Decrypt
        decrypted_data = encryptor.decrypt_fields(encrypted_data, ["name", "email"])

        if decrypted_data["name"] != "John Doe":
            raise AssertionError
        if decrypted_data["email"] != "john@example.com":
            raise AssertionError
        if decrypted_data["id"] != "123":
            raise AssertionError
        if "_encryption_info" in decrypted_data:
            raise AssertionError

    def test_encrypt_artifact_fields(self):
        """Test encrypting artifact fields."""
        password = "test_password"
        artifact = {
            "id": "artifact_123",
            "title": "Secret Document",
            "content": "This is confidential content",
            "author": "John Doe",
            "tags": ["confidential", "secret"],
        }

        encryptor = ArtifactEncryption(password)
        encrypted = encryptor.encrypt_artifact_fields(artifact, ["content", "author"])

        if encrypted["content"] == "This is confidential content":
            raise AssertionError
        if encrypted["author"] == "John Doe":
            raise AssertionError
        if encrypted["title"] != "Secret Document":
            raise AssertionError
        if encrypted["encrypted_fields"] != "content,author":
            raise AssertionError

    def test_decrypt_artifact_fields(self):
        """Test decrypting artifact fields."""
        password = "test_password"
        artifact = {
            "id": "artifact_123",
            "title": "Secret Document",
            "content": "This is confidential content",
            "author": "John Doe",
            "encrypted_fields": "content,author",
        }

        encryptor = ArtifactEncryption(password)
        encrypted = encryptor.encrypt_artifact_fields(artifact, ["content", "author"])
        decrypted = encryptor.decrypt_artifact_fields(encrypted)

        if decrypted["content"] != "This is confidential content":
            raise AssertionError
        if decrypted["author"] != "John Doe":
            raise AssertionError
        if decrypted["title"] != "Secret Document":
            raise AssertionError
        if "encrypted_fields" in decrypted:
            raise AssertionError

    def test_decrypt_artifact_no_encrypted_fields(self):
        """Test decrypting artifact with no encrypted fields."""
        artifact = {"id": "artifact_123", "title": "Public Document"}

        encryptor = ArtifactEncryption("password")
        result = encryptor.decrypt_artifact_fields(artifact)

        if result != artifact:
            raise AssertionError

    def test_generate_encryption_key_id(self):
        """Test generating encryption key ID."""
        encryptor = ArtifactEncryption()

        key_id1 = encryptor.generate_encryption_key_id()
        key_id2 = encryptor.generate_encryption_key_id()

        assert isinstance(key_id1, str)
        if len(key_id1) <= 0:
            raise AssertionError
        if key_id1 == key_id2:
            raise AssertionError

    def test_rotate_encryption(self):
        """Test rotating encryption with new password."""
        old_password = "old_password"
        new_password = "new_password"
        data = {"id": "123", "secret": "This is secret data"}

        # Encrypt with old password
        old_encryptor = ArtifactEncryption(old_password)
        encrypted = old_encryptor.encrypt_fields(data, ["secret"])

        # Rotate to new password
        rotated = old_encryptor.rotate_encryption(encrypted, old_password, new_password, ["secret"])

        # Decrypt with new password
        new_encryptor = ArtifactEncryption(new_password)
        decrypted = new_encryptor.decrypt_fields(rotated, ["secret"])

        if decrypted["secret"] != "This is secret data":
            raise AssertionError
        if decrypted["id"] != "123":
            raise AssertionError

    def test_encrypt_complex_data_types(self):
        """Test encrypting complex data types (dict, list)."""
        password = "test_password"
        data = {
            "id": "123",
            "metadata": {"tags": ["tag1", "tag2"], "properties": {"key": "value"}},
        }

        encryptor = ArtifactEncryption(password)
        encrypted = encryptor.encrypt_fields(data, ["metadata"])

        # Should be able to decrypt back
        decrypted = encryptor.decrypt_fields(encrypted, ["metadata"])
        if decrypted["metadata"] != data["metadata"]:
            raise AssertionError


class TestConvenienceFunctions:
    """Test cases for convenience functions."""

    def test_encrypt_text(self):
        """Test encrypt_text convenience function."""
        password = "test_password"
        text = "Hello, World!"

        encrypted = encrypt_text(text, password)

        assert isinstance(encrypted, str)
        # Should be base64 encoded
        assert len(encrypted) > len(text)

    def test_decrypt_text(self):
        """Test decrypt_text convenience function."""
        password = "test_password"
        original_text = "Hello, World!"

        encrypted = encrypt_text(original_text, password)
        decrypted = decrypt_text(encrypted, password)

        if decrypted != original_text:
            raise AssertionError

    def test_encrypt_decrypt_text_roundtrip(self):
        """Test full roundtrip of encrypt/decrypt text."""
        password = "my_secret_password"
        test_cases = [
            "Simple text",
            "Text with special characters: !@#$%^&*()",
            "Unicode: 你好世界 🌍",
            "Very long text " * 100,
        ]

        for text in test_cases:
            encrypted = encrypt_text(text, password)
            decrypted = decrypt_text(encrypted, password)
            if decrypted != text:
                raise AssertionError


class TestArtifactEncryptionIntegration:
    """Integration tests for ArtifactEncryption."""

    def test_full_artifact_workflow(self):
        """Test complete artifact encryption/decryption workflow."""
        password = "integration_test_password"

        # Original artifact
        artifact = {
            "id": "ART_001",
            "title": "Confidential Report",
            "summary": "This is a public summary",
            "content": "This is highly confidential content that must be encrypted",
            "author": "John Smith",
            "reviewer": "Jane Doe",
            "metadata": {"classification": "TOP_SECRET", "department": "Research"},
            "attachments": ["file1.pdf", "file2.docx"],
        }

        encryptor = ArtifactEncryption(password)

        # Encrypt sensitive fields
        sensitive_fields = ["content", "author", "reviewer", "metadata"]
        encrypted_artifact = encryptor.encrypt_artifact_fields(artifact, sensitive_fields)

        # Verify encryption
        if encrypted_artifact["content"] == artifact["content"]:
            raise AssertionError
        if encrypted_artifact["author"] == artifact["author"]:
            raise AssertionError
        if encrypted_artifact["summary"] != artifact["summary"]:
            raise AssertionError
        if encrypted_artifact["attachments"] != artifact["attachments"]:
            raise AssertionError

        # Decrypt
        decrypted_artifact = encryptor.decrypt_artifact_fields(encrypted_artifact)

        # Verify decryption
        if decrypted_artifact["content"] != artifact["content"]:
            raise AssertionError
        if decrypted_artifact["author"] != artifact["author"]:
            raise AssertionError
        if decrypted_artifact["reviewer"] != artifact["reviewer"]:
            raise AssertionError
        if decrypted_artifact["metadata"] != artifact["metadata"]:
            raise AssertionError
        if decrypted_artifact["summary"] != artifact["summary"]:
            raise AssertionError
        if decrypted_artifact["attachments"] != artifact["attachments"]:
            raise AssertionError

    def test_multiple_encryptors_same_password(self):
        """Test that different encryptor instances with same password work together."""
        password = "shared_password"
        data = "Test data for sharing"

        encryptor1 = ArtifactEncryption(password)
        encryptor2 = ArtifactEncryption(password)

        # Encrypt with first encryptor
        encrypted = encryptor1.encrypt_data(data)

        # Decrypt with second encryptor
        decrypted = encryptor2.decrypt_data(encrypted)

        if decrypted.decode("utf-8") != data:
            raise AssertionError

    def test_different_passwords_isolation(self):
        """Test that different passwords produce different results."""
        data = "Test data"
        password1 = "password1"
        password2 = "password2"

        encryptor1 = ArtifactEncryption(password1)
        encryptor2 = ArtifactEncryption(password2)

        encrypted1 = encryptor1.encrypt_data(data)
        encrypted2 = encryptor2.encrypt_data(data)

        # Should be different
        if encrypted1["data"] == encrypted2["data"]:
            raise AssertionError
        if encrypted1["salt"] == encrypted2["salt"]:
            raise AssertionError

        # Should not be decryptable with wrong password
        with pytest.raises(Exception):  # Cryptography will raise an exception
            encryptor1.decrypt_data(encrypted2)

    def test_empty_fields_encryption(self):
        """Test encrypting empty or None fields."""
        password = "test_password"
        data = {
            "id": "123",
            "empty_string": "",
            "none_value": None,
            "normal_field": "normal value",
        }

        encryptor = ArtifactEncryption(password)

        # Should handle empty string
        encrypted = encryptor.encrypt_fields(data, ["empty_string"])
        decrypted = encryptor.decrypt_fields(encrypted, ["empty_string"])
        if decrypted["empty_string"] != "":
            raise AssertionError

        # Should handle None value
        encrypted = encryptor.encrypt_fields(data, ["none_value"])
        decrypted = encryptor.decrypt_fields(encrypted, ["none_value"])
        if decrypted["none_value"] is not None:
            raise AssertionError


class TestErrorHandling:
    """Test cases for error handling in encryption."""

    def test_decrypt_invalid_data(self):
        """Test decrypting invalid encrypted data."""
        encryptor = ArtifactEncryption("password")

        invalid_data = {
            "data": "invalid_base64!",
            "salt": "invalid_salt",
            "iv": "invalid_iv",
        }

        with pytest.raises(Exception):
            encryptor.decrypt_data(invalid_data)

    def test_decrypt_tampered_data(self):
        """Test decrypting tampered encrypted data."""
        password = "test_password"
        data = "Original data"

        encryptor = ArtifactEncryption(password)
        encrypted = encryptor.encrypt_data(data)

        # Tamper with encrypted data
        tampered = encrypted.copy()
        tampered["data"] = "tampered_data"

        with pytest.raises(Exception):
            encryptor.decrypt_data(tampered)

    def test_wrong_password_decryption(self):
        """Test decrypting with wrong password."""
        data = "Secret data"

        encryptor1 = ArtifactEncryption("correct_password")
        encrypted = encryptor1.encrypt_data(data)

        encryptor2 = ArtifactEncryption("wrong_password")

        with pytest.raises(Exception):
            encryptor2.decrypt_data(encrypted)
