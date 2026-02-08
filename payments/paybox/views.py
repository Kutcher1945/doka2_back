# import hashlib
# from xml.etree.ElementTree import fromstring
#
# import requests
# from rest_framework import status, permissions, viewsets
# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.permissions import IsAuthenticated, AllowAny
# from rest_framework.response import Response
#
# from .serializers import *
#
# CustomUser = get_user_model()
#
#
# class UserWalletViewSet(viewsets.ModelViewSet):
#     permission_classes = [permissions.AllowAny]
#     serializer_class = UserPayBoxSerializer
#     queryset = User.objects.all()
#
#
# @api_view(['GET'])
# @permission_classes([AllowAny])
# def get_balance_user(request):
#     user_id = request.GET.get('user_id')
#     # current_user = User.objects.get(pk=user_id)
#     current_user = CustomUser.objects.filter(id=user_id).first()
#     user_wallet = UserWallet.objects.filter(user=current_user).first()
#     ser = UserWalletSerializer(user_wallet)
#     return Response(ser.data)
#
#
# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def initPayment(request):
#     data = {}
#     price = request.query_params.get('price')
#     data['pg_order_id'] = request.user.id
#     data['pg_merchant_id'] = 539655
#     data['pg_amount'] = price
#     data['pg_description'] = 'Ticket'
#     data['pg_salt'] = 'molbulak'
#     sign = 'init_payment.php;{0};{1};{2};{3};{4};HnfHbsydrNakinn3'.format(data.get('pg_amount'),
#                                                                           data.get('pg_description'),
#                                                                           data.get('pg_merchant_id'),
#                                                                           data.get('pg_order_id'),
#                                                                           data.get('pg_salt'))
#     result = hashlib.md5(sign.encode())
#     hash = result.hexdigest()
#     data['pg_sig'] = hash
#
#     r = requests.post('https://api.paybox.money/init_payment.php', data=data)
#     myxml = fromstring(r.text)
#     pg_redirect_url = myxml.find('./pg_redirect_url').text
#     return Response({'url': pg_redirect_url}, status=status.HTTP_200_OK)
#
#
# @api_view(['POST', 'PUT'])
# @permission_classes([AllowAny])
# def test(request):
#     try:
#         data = request.data
#         pg_order_id = int(data.get('pg_order_id'))
#         pg_ps_amount = int(data.get('pg_ps_amount'))
#
#         c_user = get_user_model().objects.get(pk=pg_order_id)
#         user_wallet = UserWallet.objects.filter(user=c_user).first()
#         if not user_wallet:
#             user_wallet = UserWallet()
#             user_wallet.user = c_user
#             user_wallet.order_id = pg_order_id
#             user_wallet.balance = pg_ps_amount
#         else:
#             user_wallet.balance += pg_ps_amount
#         if user_wallet.bonus_balance == 0:
#             user_wallet.bonus_balance = int(pg_ps_amount * 0.3)
#         user_wallet.save()
#         count = WalletHistory.objects.filter(user_wallet=user_wallet).count() + 1
#         user_wallet.create_history(count, pg_ps_amount)
#     except Exception as e:
#         test = Test()
#         test.name = request.data
#         test.surname = e
#         test.save()
#         return Response('test_id {}'.format(test.id), status=status.HTTP_400_BAD_REQUEST)
#     return Response('good', status=status.HTTP_200_OK)

