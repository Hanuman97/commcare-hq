function SMSPhoneNumberViewModel(initial_value) {
    var model = this;

    this.filter_type = ko.observable(initial_value.filter_type || 'phone_number');
    this.phone_number_filter = ko.observable(initial_value.phone_number_filter || '');
    this.has_phone_number = ko.observable(initial_value.has_phone_number);
    this.contact_type = ko.observable(initial_value.contact_type);
    this.verification_status = ko.observable(initial_value.verification_status);

    this.phone_number_options = ko.pureComputed(function () {
        if (model.contact_type() === 'cases') {
            return ['That have phone numbers'];
        }
        return [
            'That have phone numbers',
            'That do not have phone numbers'
        ];
    });

    this.show_phone_filter = ko.pureComputed(function () {
        return model.filter_type() === 'phone_number';
    });

    this.show_contact_filter = ko.pureComputed(function () {
        return model.filter_type() === 'contact';
    });

    this.show_group_filter = ko.pureComputed(function () {
        return model.show_contact_filter() && model.contact_type() === 'users';
    });

    this.can_edit_has_phone_number = ko.pureComputed(function () {
        return model.show_contact_filter() && model.contact_type() === 'cases';
    });

    this.show_verification_filter = ko.pureComputed(function () {
        return model.show_contact_filter() && model.has_phone_number() === 'That have phone numbers';
    });
}
