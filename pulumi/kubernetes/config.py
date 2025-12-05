"""Kubernetes configuration resources"""
import pulumi
import pulumi_kubernetes as k8s


def create_namespace(
    provider: k8s.Provider,
    name: str = "agriguard"
) -> k8s.core.v1.Namespace:
    """Create Kubernetes namespace"""
    
    namespace = k8s.core.v1.Namespace(
        "agriguard-namespace",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name=name,
            labels={
                "app": "agriguard",
                "managed-by": "pulumi",
            }
        ),
        opts=pulumi.ResourceOptions(provider=provider)
    )
    
    return namespace


def create_configmap(
    provider: k8s.Provider,
    namespace: k8s.core.v1.Namespace
) -> k8s.core.v1.ConfigMap:
    """Create ConfigMap with service URLs"""
    
    config_map = k8s.core.v1.ConfigMap(
        "agriguard-config",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name="agriguard-config",
            namespace=namespace.metadata.name,
        ),
        data={
            "GCP_PROJECT_ID": "agriguard-ac215",
            "MCSI_URL": "http://mcsi-service:8000",
            "YIELD_URL": "http://yield-service:8001",
            "RAG_URL": "http://rag-service:8003",
            "CHROMADB_HOST": "chromadb-service",
            "CHROMADB_PORT": "8000",
            "RAG_COLLECTION_NAME": "corn-stress-knowledge",
            "GEMINI_MODEL": "gemini-2.0-flash",
            "PYTHONUNBUFFERED": "1",
        },
        opts=pulumi.ResourceOptions(
            provider=provider,
            depends_on=[namespace]
        )
    )
    
    return config_map


def create_secrets(
    provider: k8s.Provider,
    namespace: k8s.core.v1.Namespace,
    gemini_api_key: str,
    gcp_sa_key_json: str
) -> k8s.core.v1.Secret:
    """Create Secret for sensitive data"""
    
    secret = k8s.core.v1.Secret(
        "agriguard-secrets",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name="agriguard-secrets",
            namespace=namespace.metadata.name,
        ),
        type="Opaque",
        string_data={
            "GEMINI_API_KEY": gemini_api_key,
            "gcp-key.json": gcp_sa_key_json,
        },
        opts=pulumi.ResourceOptions(
            provider=provider,
            depends_on=[namespace]
        )
    )
    
    return secret
