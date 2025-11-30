# listings/serializers.py
from rest_framework import serializers
from .models import Listing, Booking, Review, ListingImage
from django.utils import timezone
from datetime import date


class ListingImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingImage
        fields = ['id', 'image', 'caption', 'is_primary', 'order', 'created_at']
        read_only_fields = ['id', 'created_at']


class ListingSerializer(serializers.ModelSerializer):
    images = ListingImageSerializer(many=True, read_only=True)
    average_rating = serializers.ReadOnlyField()
    review_count = serializers.ReadOnlyField()
    host_name = serializers.CharField(source='host.username', read_only=True)
    is_available = serializers.SerializerMethodField()
    
    class Meta:
        model = Listing
        fields = [
            'id', 'title', 'description', 'property_type', 'address', 'city',
            'state', 'country', 'zip_code', 'latitude', 'longitude', 'max_guests',
            'bedrooms', 'beds', 'bathrooms', 'wifi', 'kitchen', 'parking', 'pool',
            'air_conditioning', 'heating', 'tv', 'base_price', 'cleaning_fee',
            'security_deposit', 'host', 'host_name', 'status', 'created_at',
            'updated_at', 'check_in_time', 'check_out_time', 'minimum_stay',
            'maximum_stay', 'average_rating', 'review_count', 'images', 'is_available'
        ]
        read_only_fields = ['host', 'created_at', 'updated_at', 'average_rating', 'review_count']
    
    def get_is_available(self, obj):
        """Check if listing is available for default dates (next 30 days)"""
        check_in = date.today()
        check_out = check_in + timezone.timedelta(days=30)
        return obj.is_available(check_in, check_out)


class CreateListingSerializer(serializers.ModelSerializer):
    """Serializer for creating new listings (includes all required fields)"""
    class Meta:
        model = Listing
        fields = [
            'title', 'description', 'property_type', 'address', 'city', 'state',
            'country', 'zip_code', 'max_guests', 'bedrooms', 'beds', 'bathrooms',
            'wifi', 'kitchen', 'parking', 'pool', 'air_conditioning', 'heating', 'tv',
            'base_price', 'cleaning_fee', 'security_deposit', 'check_in_time',
            'check_out_time', 'minimum_stay', 'maximum_stay'
        ]
    
    def create(self, validated_data):
        # Set the host to the current user
        validated_data['host'] = self.context['request'].user
        return super().create(validated_data)


class BookingSerializer(serializers.ModelSerializer):
    listing_title = serializers.CharField(source='listing.title', read_only=True)
    listing_city = serializers.CharField(source='listing.city', read_only=True)
    listing_country = serializers.CharField(source='listing.country', read_only=True)
    guest_name = serializers.CharField(source='guest.username', read_only=True)
    guest_email = serializers.CharField(source='guest.email', read_only=True)
    duration = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    can_be_cancelled = serializers.ReadOnlyField()
    total_price_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Booking
        fields = [
            'id', 'listing', 'listing_title', 'listing_city', 'listing_country',
            'guest', 'guest_name', 'guest_email', 'check_in', 'check_out',
            'number_of_guests', 'guest_special_requests', 'total_price',
            'total_price_display', 'security_deposit_held', 'status', 'duration',
            'is_active', 'can_be_cancelled', 'payment_status', 'created_at',
            'updated_at', 'confirmed_at', 'cancelled_at', 'payment_intent_id'
        ]
        read_only_fields = [
            'id', 'guest', 'total_price', 'security_deposit_held', 'status',
            'created_at', 'updated_at', 'confirmed_at', 'cancelled_at',
            'payment_intent_id', 'duration', 'is_active', 'can_be_cancelled'
        ]
    
    def get_total_price_display(self, obj):
        return f"${obj.total_price:.2f}"


class CreateBookingSerializer(serializers.ModelSerializer):
    """Serializer for creating new bookings with validation"""
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    duration = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Booking
        fields = [
            'listing', 'check_in', 'check_out', 'number_of_guests',
            'guest_special_requests', 'total_price', 'duration'
        ]
    
    def validate(self, data):
        # Check if check-out is after check-in
        if data['check_in'] >= data['check_out']:
            raise serializers.ValidationError("Check-out date must be after check-in date.")
        
        # Check if dates are in the future
        if data['check_in'] < date.today():
            raise serializers.ValidationError("Check-in date cannot be in the past.")
        
        listing = data['listing']
        
        # Check if listing is available
        if not listing.is_available(data['check_in'], data['check_out']):
            raise serializers.ValidationError("This listing is not available for the selected dates.")
        
        # Check guest count
        if data['number_of_guests'] > listing.max_guests:
            raise serializers.ValidationError(
                f"This listing accommodates maximum {listing.max_guests} guests."
            )
        
        # Check minimum stay
        duration = (data['check_out'] - data['check_in']).days
        if duration < listing.minimum_stay:
            raise serializers.ValidationError(
                f"Minimum stay for this listing is {listing.minimum_stay} nights."
            )
        
        # Check maximum stay
        if duration > listing.maximum_stay:
            raise serializers.ValidationError(
                f"Maximum stay for this listing is {listing.maximum_stay} nights."
            )
        
        # Add duration to validated data for use in create method
        data['duration'] = duration
        return data
    
    def create(self, validated_data):
        # Calculate total price
        listing = validated_data['listing']
        duration = validated_data.pop('duration')  # Remove duration as it's not a model field
        base_cost = duration * listing.base_price
        total_price = base_cost + listing.cleaning_fee
        
        # Set the guest to the current user
        validated_data['guest'] = self.context['request'].user
        validated_data['total_price'] = total_price
        validated_data['security_deposit_held'] = listing.security_deposit
        
        return super().create(validated_data)


class ReviewSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.username', read_only=True)
    author_email = serializers.CharField(source='author.email', read_only=True)
    listing_title = serializers.CharField(source='listing.title', read_only=True)
    booking_check_in = serializers.DateField(source='booking.check_in', read_only=True)
    booking_check_out = serializers.DateField(source='booking.check_out', read_only=True)
    
    class Meta:
        model = Review
        fields = [
            'id', 'listing', 'listing_title', 'booking', 'author', 'author_name',
            'author_email', 'rating', 'title', 'comment', 'host_response',
            'host_response_at', 'is_verified', 'is_public', 'created_at',
            'updated_at', 'booking_check_in', 'booking_check_out'
        ]
        read_only_fields = [
            'id', 'author', 'listing', 'created_at', 'updated_at',
            'host_response_at', 'is_verified'
        ]
    
    def validate(self, data):
        # Ensure the user can only review their own completed bookings
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            booking = self.instance.booking if self.instance else data.get('booking')
            if booking:
                if booking.guest != request.user:
                    raise serializers.ValidationError("You can only review your own bookings.")
                
                if booking.status != 'completed':
                    raise serializers.ValidationError("You can only review completed bookings.")
        
        return data
    
    def create(self, validated_data):
        # Set the author to the current user and listing from booking
        validated_data['author'] = self.context['request'].user
        booking = validated_data['booking']
        validated_data['listing'] = booking.listing
        
        # Mark as verified since it's linked to a real booking
        validated_data['is_verified'] = True
        
        return super().create(validated_data)


class HostResponseSerializer(serializers.ModelSerializer):
    """Serializer for hosts to respond to reviews"""
    class Meta:
        model = Review
        fields = ['host_response']
    
    def update(self, instance, validated_data):
        validated_data['host_response_at'] = timezone.now()
        return super().update(instance, validated_data)


class BookingStatusSerializer(serializers.ModelSerializer):
    """Serializer for updating booking status"""
    class Meta:
        model = Booking
        fields = ['status']
    
    def validate_status(self, value):
        valid_transitions = {
            'pending': ['confirmed', 'cancelled'],
            'confirmed': ['active', 'cancelled'],
            'active': ['completed'],
            'completed': [],
            'cancelled': []
        }
        
        current_status = self.instance.status
        if value not in valid_transitions[current_status]:
            raise serializers.ValidationError(
                f"Cannot change status from {current_status} to {value}"
            )
        
        return value
    
    def update(self, instance, validated_data):
        new_status = validated_data['status']
        
        # Set timestamps based on status changes
        if new_status == 'confirmed' and instance.status == 'pending':
            validated_data['confirmed_at'] = timezone.now()
        elif new_status == 'cancelled' and instance.status in ['pending', 'confirmed']:
            validated_data['cancelled_at'] = timezone.now()
        
        return super().update(instance, validated_data)


class ListingSearchSerializer(serializers.Serializer):
    """Serializer for listing search parameters"""
    city = serializers.CharField(required=False)
    country = serializers.CharField(required=False)
    check_in = serializers.DateField(required=False)
    check_out = serializers.DateField(required=False)
    guests = serializers.IntegerField(required=False, min_value=1)
    property_type = serializers.CharField(required=False)
    min_price = serializers.DecimalField(required=False, max_digits=10, decimal_places=2, min_value=0)
    max_price = serializers.DecimalField(required=False, max_digits=10, decimal_places=2, min_value=0)
    amenities = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    
    def validate(self, data):
        if data.get('check_in') and data.get('check_out'):
            if data['check_in'] >= data['check_out']:
                raise serializers.ValidationError("Check-out date must be after check-in date.")
        
        return data