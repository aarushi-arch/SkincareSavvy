from rest_framework.views import APIView
from rest_framework.response import Response

class ShopHealthCheck(APIView):
    def get(self, request):
        return Response({"status": "shop app working"})
