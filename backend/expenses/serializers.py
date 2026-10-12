from rest_framework import serializers

from .models import Category, Transaction


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'type']


class TransactionSerializer(serializers.ModelSerializer):
    # 'type' is optional here because /api/expenses/ and /api/income/ set it automatically.
    type = serializers.ChoiceField(choices=Transaction._meta.get_field('type').choices, required=False)

    class Meta:
        model = Transaction
        fields = ['id', 'wallet', 'category', 'amount', 'type',
                  'description', 'transaction_date', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Amount must be greater than zero.')
        return value

    def validate_wallet(self, wallet):
        if wallet.user != self.context['request'].user:
            raise serializers.ValidationError('This wallet is not yours.')
        return wallet

    def validate(self, data):
        view = self.context.get('view')
        tx_type = data.get('type') or getattr(view, 'forced_type', None) or getattr(self.instance, 'type', None)
        if not tx_type:
            raise serializers.ValidationError({'type': 'This field is required.'})
        category = data.get('category')
        if category:
            if category.user_id not in (None, self.context['request'].user.id):
                raise serializers.ValidationError({'category': 'This category is not yours.'})
            if category.type != tx_type:
                raise serializers.ValidationError('Category type does not match transaction type.')
        return data
