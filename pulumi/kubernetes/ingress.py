"""Kubernetes Ingress for external access"""
import pulumi
import pulumi_kubernetes as k8s


def create_ingress(
    provider: k8s.Provider,
    namespace: k8s.core.v1.Namespace,
    services: dict
) -> k8s.networking.v1.Ingress:
    """Create Ingress for external access"""
    
    ingress = k8s.networking.v1.Ingress(
        "agriguard-ingress",
        metadata=k8s.meta.v1.ObjectMetaArgs(
            name="agriguard-ingress",
            namespace=namespace.metadata.name,
            annotations={
                "kubernetes.io/ingress.class": "gce",
            }
        ),
        spec=k8s.networking.v1.IngressSpecArgs(
            rules=[k8s.networking.v1.IngressRuleArgs(
                http=k8s.networking.v1.HTTPIngressRuleValueArgs(
                    paths=[
                        k8s.networking.v1.HTTPIngressPathArgs(
                            path="/api/*",
                            path_type="ImplementationSpecific",
                            backend=k8s.networking.v1.IngressBackendArgs(
                                service=k8s.networking.v1.IngressServiceBackendArgs(
                                    name=services['api'].metadata.name,
                                    port=k8s.networking.v1.ServiceBackendPortArgs(
                                        number=8000
                                    )
                                )
                            )
                        ),
                        k8s.networking.v1.HTTPIngressPathArgs(
                            path="/*",
                            path_type="ImplementationSpecific",
                            backend=k8s.networking.v1.IngressBackendArgs(
                                service=k8s.networking.v1.IngressServiceBackendArgs(
                                    name=services['frontend'].metadata.name,
                                    port=k8s.networking.v1.ServiceBackendPortArgs(
                                        number=3000
                                    )
                                )
                            )
                        ),
                    ]
                )
            )]
        ),
        opts=pulumi.ResourceOptions(
            provider=provider,
            depends_on=[namespace, services['api'], services['frontend']]
        )
    )
    
    return ingress
