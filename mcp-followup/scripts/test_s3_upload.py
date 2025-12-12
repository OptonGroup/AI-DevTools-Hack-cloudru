"""Тестовый скрипт для проверки загрузки файлов в S3 Cloud.ru."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

import httpx


async def get_iam_token(key_id: str, key_secret: str) -> str:
    """Получить IAM токен от Cloud.ru."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://iam.api.cloud.ru/api/v1/auth/token",
            json={"keyId": key_id, "secret": key_secret},
            headers={"Content-Type": "application/json"}
        )
        print(f"   IAM Response: {response.status_code}")
        print(f"   IAM Body: {response.text[:500]}")
        response.raise_for_status()
        data = response.json()
        # Пробуем разные варианты ключа
        return data.get("token") or data.get("access_token") or data.get("accessToken") or str(data)


async def test_s3_upload():
    """Тестируем загрузку файла в S3 Cloud.ru."""
    
    print("=" * 60)
    print("S3 Cloud.ru Upload Test (IAM Auth)")
    print("=" * 60)
    
    # Проверяем переменные окружения
    endpoint = os.getenv("CLOUD_RAG_S3_ENDPOINT")
    bucket = os.getenv("CLOUD_RAG_S3_BUCKET")
    key_id = os.getenv("CLOUD_RAG_KEY_ID")
    key_secret = os.getenv("CLOUD_RAG_KEY_SECRET")
    
    print(f"\nEndpoint: {endpoint}")
    print(f"Bucket: {bucket}")
    print(f"Key ID: {key_id[:10]}..." if key_id else "Key ID: NOT SET")
    print(f"Key Secret: {'***' if key_secret else 'NOT SET'}")
    
    if not all([endpoint, bucket, key_id, key_secret]):
        print("\n❌ Не все переменные окружения настроены!")
        return False
    
    try:
        # 1. Получаем IAM токен
        print("\n1. Получаем IAM токен...")
        token = await get_iam_token(key_id, key_secret)
        print(f"   ✅ Токен получен: {token[:20]}...")
        
        # 2. Загружаем тестовый файл
        print("\n2. Загружаем тестовый файл...")
        
        test_content = """# Тестовый документ

Это тестовый документ для проверки загрузки в S3 Cloud.ru.

**Дата:** 2025-12-11
**Тест:** Успешно
"""
        
        tenant_id = os.getenv("CLOUD_RAG_TENANT_ID", "83488eec-b299-4b76-ba13-e95ed3b1570a")
        
        # Пробуем разные форматы URL и заголовков
        test_variants = [
            # Вариант 1: tenant в subdomain
            (f"https://{tenant_id}.s3.cloud.ru/{bucket}/test/test_document.md", {}),
            # Вариант 2: tenant в path
            (f"https://s3.cloud.ru/{tenant_id}/{bucket}/test/test_document.md", {}),
            # Вариант 3: стандартный URL с x-amz-tenant-id header
            (f"{endpoint}/test/test_document.md", {"x-amz-tenant-id": tenant_id}),
            # Вариант 4: tenant как query param
            (f"{endpoint}/test/test_document.md?tenant-id={tenant_id}", {}),
        ]
        
        async with httpx.AsyncClient() as client:
            for i, (url, extra_headers) in enumerate(test_variants, 1):
                print(f"   Вариант {i}: {url[:60]}...")
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "text/markdown",
                    **extra_headers
                }
                response = await client.put(url, content=test_content.encode('utf-8'), headers=headers)
                print(f"      Status: {response.status_code}")
                
                if response.status_code in (200, 201):
                    print(f"      ✅ Успех!")
                    upload_url = url
                    break
                else:
                    print(f"      Error: {response.text[:100]}")
            
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200] if response.text else 'empty'}")
            
            if response.status_code in (200, 201):
                print(f"   ✅ Файл загружен!")
            else:
                print(f"   ❌ Ошибка загрузки")
                return False
        
        # 3. Проверяем что файл загрузился (GET)
        print("\n3. Проверяем загруженный файл...")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                upload_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-Tenant-Id": tenant_id,
                }
            )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   ✅ Файл читается!")
                print(f"   Content: {response.text[:100]}...")
            else:
                print(f"   ❌ Файл не найден")
        
        # 4. Тест загрузки PDF
        print("\n4. Тест загрузки PDF...")
        
        test_pdf_path = os.path.join(os.path.dirname(__file__), '..', 'test_output.pdf')
        if os.path.exists(test_pdf_path):
            with open(test_pdf_path, 'rb') as f:
                pdf_content = f.read()
            
            pdf_url = f"{endpoint}/test/test_conference.pdf"
            
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    pdf_url,
                    content=pdf_content,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/pdf",
                        "X-Tenant-Id": tenant_id,
                    }
                )
                
                print(f"   Status: {response.status_code}")
                
                if response.status_code in (200, 201):
                    print(f"   ✅ PDF загружен! ({len(pdf_content)} bytes)")
                else:
                    print(f"   ❌ Ошибка: {response.text}")
        else:
            print(f"   ⚠️ PDF не найден, пропускаем")
        
        print("\n" + "=" * 60)
        print("✅ Тесты S3 завершены!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import asyncio
    success = asyncio.run(test_s3_upload())
    sys.exit(0 if success else 1)
