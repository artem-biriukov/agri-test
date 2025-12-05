"""Kubernetes Service resources"""
import pulumi
import pulumi_kubernetes as k8s


def create_service(
    provider: k8s.Provider,
    namespace: k8s.core.v1.Namespace,
    deployment: k8s.apps.v1.Deployment,
    name: str,
    port: int,
) -> k8s.core.v1.Service:
    """Create Kubernetes Service"""
    
    service = k8s.core.v1.Service(
        f"{name}-service",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name=f"{name}-service",
            namespace=namespace.metadata.name,
            labels={"app": name}
        ),
        spec=k8s.core.v1.ServiceSpecArgs(
            selector={"app": name},
            ports=[k8s.core.v1.ServicePortArgs(
                port=port,
                target_port=port,
                protocol="TCP",
                name="http"
            )],
            type="ClusterIP",
        ),
        opts=pulumi.ResourceOptions(
            provider=provider,
            depends_on=[namespace, deployment]
        )
    )
    
    return service


def create_all_services(
    provider: k8s.Provider,
    namespace: k8s.core.v1.Namespace,
    deployments: dict
) -> dict:
    """Create services for all deployments"""
    
    return {
        'mcsi': create_service(provider, namespace, deployments['mcsi'], "mcsi", 8000),
        'yield': create_service(provider, namespace, deployments['yield'], "yield", 8001),
        'api': create_service(provider, namespace, deployments['api'], "api", 8000),
        'chromadb': create_service(provider, namespace, deployments['chromadb'], "chromadb", 8000),
        'rag': create_service(provider, namespace, deployments['rag'], "rag", 8003),
        'frontend': create_service(provider, namespace, deployments['frontend'], "frontend", 3000),
    }
