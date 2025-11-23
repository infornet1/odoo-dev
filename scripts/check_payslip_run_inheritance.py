# Check if hr.payslip.run inherits from mail.thread

model = env['hr.payslip.run']
print(f"Model: {model._name}")
print(f"Inherits: {model._inherit}")
print(f"Has message_post: {hasattr(model, 'message_post')}")

if hasattr(model, '_inherits'):
    print(f"Delegation inheritance: {model._inherits}")

# Check the model class hierarchy
print(f"\nMRO (Method Resolution Order):")
for cls in model.__class__.__mro__[:10]:
    print(f"  - {cls}")
